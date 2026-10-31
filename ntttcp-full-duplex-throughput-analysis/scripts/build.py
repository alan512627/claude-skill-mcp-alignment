import json, sys, os, re, glob
here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, here)
import evlib as E
from evlib import ev, ev_text, grep, secs

scratch, out, evdir = sys.argv[1], sys.argv[2], sys.argv[3]
E.init({"s2": os.path.join(scratch, "log_extract"), "s46": os.path.join(scratch, "log46")})
LAB = E.LABEL
C = "<code>{}</code>".format
METRICS = "backgroundmonitors/rackmanagersystemsensoroobmonitor_metrics.log"
DRV = C("D:\\Users\\PSE\\sdkagent\\packages\\CrcSdk\\tools\\pcietool\\Drivers\\rdsysinfo.sys")
EXTRA = {}  # extra evidence files written by us (sensor excerpts)


# ------------------------------------------------------------------ parsing helpers
def threads(name):
    rows = [l.strip().split(",") for l in open(os.path.join(scratch, name), encoding="utf-8-sig") if l.strip()]
    return [float(v) for _, v in rows]


def sensors(name):
    s = json.load(open(os.path.join(here, name)))
    return s, {x["name"]: x for x in s["stats"]}


def cmd_windows(slot, phase):
    """{command: (start_hms, end_hms)} from Summary-Invoke-Profile.log"""
    w, cur = {}, {}
    for no, l in grep(slot, f"{phase}/Summary-Invoke-Profile.log", r"Invoking Command|Command (success|failed)"):
        m = re.match(r"\s*\S+T(\d\d:\d\d:\d\d)Z\s+Invoking Command\s+\|\s+\|\s+(\S+)", l)
        if m:
            cur = {"name": m.group(2), "s": m.group(1)}
            continue
        m = re.match(r"\s*\S+T(\d\d:\d\d:\d\d)Z\s+Command (?:success|failed[^|]*?)\s*\|[^|]*\|\s+(\S+)", l)
        if m and cur:
            w[m.group(2)] = (cur["s"], m.group(1))
    return w


def event_times(slot, phase, pat):
    rel = "Pretest/Export-WindowsSystemEvents/eventsLog-System-2*.log" if phase == "Pretest" else "Posttest/Get-SystemEventsDiagnostics/eventsLog-System-2*.log"
    res = []
    for no, l in grep(slot, rel, pat):
        m = re.search(r"Time Created: \S+ (\d\d:\d\d:\d\d)", l)
        res.append(m.group(1))
    return res


def cper(slot):
    res = []
    for phase in ("Pretest", "Posttest"):
        files = glob.glob(os.path.join(E.ROOTS[slot], phase, "cper", "CPER_*_summary.json"))
        files.sort(key=lambda p: int(re.search(r"CPER_(\d+)_", p).group(1)))
        for p in files:
            j = json.load(open(p, encoding="utf-8-sig"))
            sd = j["SectionDescriptor"][0]
            d = sd["data"]
            n = int(re.search(r"CPER_(\d+)_", p).group(1))
            nz = [k for k, v in d.items() if isinstance(v, (int, float)) and v != 0 and not k.startswith(("header", "pcie_details", "sdm_interrupt", "valid_bits"))]
            res.append({"phase": phase, "n": n, "rel": f"{phase}/cper/CPER_{n}_summary.json", "ts": j["Header"]["TimeStamp"][11:], "sev": j["Header"]["Severity"],
                        "desc": d.get("description"), "fru": sd.get("FRUText"), "did": d.get("pcie_details.device_id"), "bus": d.get("pcie_details.bus_number"),
                        "sdm": d.get("sdm_interrupt_events"), "nz": nz, "data": d, "thr": sd["Flags"]["ThresholdExceeded"]})
    return res


def metrics(slot):
    actual, L = E.lines(slot, METRICS)
    blocks, i = [], 0
    while i < len(L):
        if L[i].strip() == "{":
            s = i
            while L[i].strip() != "}":
                i += 1
            seg = L[s:i + 1]
            nm = re.search(r'"metricName": "([^"]+)"', "\n".join(seg)).group(1)
            mv = re.search(r'"metricValue": ([-\d.]+),', "\n".join(seg))
            ts = re.search(r'"timestamp": "([^"]+)"', "\n".join(seg)).group(1)
            if mv:
                blocks.append((nm, float(mv.group(1)), ts, s + 1, i + 1))
        i += 1
    return L, blocks


def smart_rows(slot):
    def load(phase):
        return json.load(open(glob.glob(os.path.join(E.ROOTS[slot], phase, "smartctl", "summary-*.json"))[0], encoding="utf-8-sig"))
    pre, post = load("Pretest"), load("Posttest")
    rows, issues = [], []
    for k in pre:
        if not k.startswith("NVMe"):
            continue
        a, b = pre[k], post[k]
        if len(a) <= 2:
            rows.append(f"{k}: 無健康欄位（storagetool-disk-inventory.log 顯示 Disk#{k[4:]} 為 FB-VIRT Virtual Disk）")
            continue

        def val(d, sub):
            for kk, vv in d.items():
                if sub in kk and isinstance(vv, dict):
                    return vv["Value"]
            return None
        parts, changed = [], False
        for label, sub in (("Media Error", "Media Error Count"), ("Critical Warning", "Critical Warning"), ("Avail Spare", "Available Spare"), ("Unsafe Shutdown", "Unsafe Shutdown"), ("Endurance Used%", "Endurance Percentage Used")):
            x, y = val(a, sub), val(b, sub)
            if x is None and y is None:
                continue
            parts.append(f"{label} {x:g}→{y:g}")
            if x != y:
                changed = True
            if label == "Media Error" and (x or y):
                issues.append(k)
        rows.append(f"{k}: " + "，".join(parts) + ("  ← 前後不同" if changed else ""))
    return rows, issues


def pcie(slot):
    _, a = E.lines(slot, "Pretest/pcietool/pcie--linkstatus.txt")
    _, b = E.lines(slot, "Posttest/pcietool/pcie--linkstatus.txt")
    dev = [l for l in b if l.startswith("BDF(")]
    bad = []
    for l in dev:
        m = re.search(r"Cur:(\S+?),(X\d+)\s+Max:(\S+?),(X\d+)", l)
        if m and (m.group(1) != m.group(3) or m.group(2) != m.group(4)):
            bad.append(l)
    return len(dev), len(bad), a == b


def tb(bps):
    return bps * 21600 / 1e12


# ------------------------------------------------------------------ per-slot
KEY = [("SOC_TMP_MAX", "SoC 最高溫", "°C"), ("DIMM_TMP_MAX", "DIMM 最高溫", "°C"), ("NODE_INLET_TMP", "進風溫度", "°C"), ("OL_S1_SOC_TMP", "OL_S1 SoC 溫度", "°C"),
       ("NODE_PWR", "Node 功耗", "W"), ("SOC_PWR", "SoC 功耗", "W"), ("FAN_HPM_1A", "風扇 HPM_1A", "RPM"), ("VR_TMP_MAX", "VR 最高溫", "°C")]
key = [{"name": n, "label": l, "u": u} for n, l, u in KEY]


def build_slot(slot, meta):
    L = LAB[slot]
    sj, sm = sensors(meta["sens"])
    nmax = max(x["n"] for x in sj["stats"])
    post_w, pre_w = cmd_windows(slot, "Posttest"), cmd_windows(slot, "Pretest")
    pcw, pcw_pre = post_w["Invoke-PcietoolChecks"], pre_w["Invoke-PcietoolChecks"]
    t7000_post = event_times(slot, "Posttest", r"Event ID: 7000.*rdsysinfo")
    t7000_pre = event_times(slot, "Pretest", r"Event ID: 7000.*rdsysinfo")
    t6008 = event_times(slot, "Pretest", r"Event ID: 6008")
    inside = lambda ts, w: all(w[0] <= t <= w[1] for t in ts)
    cp = cper(slot)
    acc = [c for c in cp if c["desc"] == "ACPI_ERROR_TYPE_VENDOR_ACCELERATOR"]
    mem = [c for c in cp if c["desc"] == "ACPI_ERROR_TYPE_PLATFORM_MEMORY"]
    assert len(acc) + len(mem) == len(cp)
    stress = meta["stress"]
    during = [c for c in cp if stress[0][11:] <= c["ts"] <= stress[1][11:]]
    pre_acc = [c for c in acc if c["phase"] == "Pretest"]
    wc_pre, wc_post = pre_w["Write-Config"], post_w["Write-Config"]
    post_acc = [c for c in acc if c["phase"] == "Posttest"]
    # 6008 vs preceding CPER
    pairs = []
    for t in t6008:
        prev = [c for c in pre_acc if 0 < secs(c["ts"], t) <= 120]
        if prev:
            pairs.append((prev[-1]["ts"], t, secs(prev[-1]["ts"], t)))
    # I2C
    def i2c(phase):
        return grep(slot, f"{phase}/bmcclishell/bmc-journal-last-2h.log", r"I2C bus\d+")
    i2c_pre, i2c_post = i2c("Pretest"), i2c("Posttest")
    hung = [x for x in i2c_pre if "bus still hung" in x[1]]
    sup_pre = [x for x in i2c_pre if "Suppress I2C bus7" in x[1]]
    sup_post = [x for x in i2c_post if "Suppress I2C bus7" in x[1]]
    rf_post = [x for x in sup_post if "recovery-fail" in x[1]]
    cnts = lambda xs: [int(re.search(r"rec_fail_cnt=(\d+)", x[1]).group(1)) for x in xs]
    other_i2c_post = [x for x in i2c_post if "bus7" not in x[1]]
    # sensors
    Lm, blocks = metrics(slot)
    polls = sorted({b[2] for b in blocks if b[0] == "NODE_PWR"})
    have = {b[2] for b in blocks if b[0] == "OL_S1_SOC_TMP"}
    miss = [p for p in polls if p not in have]
    olv = [b for b in blocks if b[0] == "OL_S1_SOC_TMP"]
    olmax = max(b[1] for b in olv)
    olmax_blocks = [b for b in olv if b[1] == olmax][:2]
    exc = []
    for b in olmax_blocks:
        exc += [f"{b[3]+i:>7}│{Lm[b[3]-1+i]}" for i in range(b[4] - b[3] + 1)]
    exc.append("")
    exc.append(f"NODE_PWR 的輪詢時間點共 {len(polls)} 個；OL_S1_SOC_TMP 有值的 {len(have)} 個；缺少的時間點（{len(miss)} 個）：")
    exc += miss
    EXTRA[f"{L}_sensor_excerpts.txt"] = "\n".join(["來源：" + METRICS, ""] + exc)
    ol_ev = [ev_text(f"[{L}] {METRICS}（摘錄：最高讀值的原始 JSON 區塊與缺少的輪詢時間點；完整檔案 9.9 MB 未收錄，請從原 zip 取用）", [e.split("│", 1)[1] if "│" in e else e for e in exc[:40]])]
    ol_ev[0]["lines"] = [[int(e.split("│")[0]), e.split("│", 1)[1]] if "│" in e and e.split("│")[0].strip().isdigit() else ["", e] for e in exc[:60]]
    # smart / pcie
    srows, sissue = smart_rows(slot)
    ndev, nbad, same = pcie(slot)
    # CSI DER
    def der(phase):
        _, DL = E.lines(slot, f"{phase}/csidiag/CSI_DER.log")
        ent = [re.sub(r"\d{4}-\d\d-\d\d \d\d:\d\d:\d\d", "<TS>", l) for l in DL if re.match(r"\s*CSI_(ERR|INFO|MODU_ERR)", l)]
        return ent, [l for l in DL if re.match(r"\s*CSI_ERR", l)], [l for l in DL if "CSI_MODU_ERR" in l], [l for l in DL if re.match(r"\s*CSI_INFO", l)]
    d_pre, d_post = der("Pretest"), der("Posttest")
    der_same = d_pre[0] == d_post[0]
    n_err, n_modu, n_info = len(d_post[1]), len(d_post[2]), len(d_post[3])
    blade_same = open(E.resolve(slot, "Pretest/bladeskucheck/BladeSkuCheck.report.txt")[0], "rb").read() == open(E.resolve(slot, "Posttest/bladeskucheck/BladeSkuCheck.report.txt")[0], "rb").read()
    n_cpld = len(grep(slot, "Posttest/bmcclishell/bmc-journal-last-2h.log", r"HPM_CPLD2|GLOBAL_CPLD"))
    n_blade = len([l for l in E.lines(slot, "Posttest/bladeskucheck/BladeSkuCheck.report.txt")[1] if re.match(r"(Error|Warning):", l)])
    # NTTTCP xml
    def xml_tail(name, pat):
        return grep(slot, f"Stress/Net_stress/{name}.xml", pat, after_last=r"</thread>")
    def xv(name, tag):
        m = [re.search(r">([-\d.]+)<", l[1]).group(1) for l in xml_tail(name, rf"<{tag}[ >]")]
        return float(m[0])
    sx = {t: xv("sender", t) for t in ("packets_sent", "packets_retransmitted", "errors", "num_processors", "cpu")}
    rx = {t: xv("receiver", t) for t in ("packets_sent", "packets_retransmitted", "errors", "num_processors", "cpu")}
    done = json.load(open(E.resolve(slot, "Stress/Net_stress/done.json")[0]))
    osc_end = E.lines(slot, "Stress/Net_stress/os_config.log")[1][-1][11:19]
    done_t = done["timestamp"][11:19]
    gap = secs(osc_end, done_t)
    sel_line = grep(slot, "Posttest/rackscm_sel_decode/selRecords.txt", r"\|")[0]
    sel_t = re.search(r"\| (\d\d:\d\d:\d\d) \|", sel_line[1]).group(1)

    # ----- findings -----
    F = []
    # 1. Posttest FAIL
    sev7045 = grep(slot, "Posttest/Get-SystemEventsDiagnostics/eventsLog-System-2*.log", r"Service File Name:.*rdsysinfo")
    F.append({"sev": "bad", "conf": "已確認", "where": "Posttest", "title": "Posttest FAIL：Get-SystemEventsDiagnostics 判定出 3 筆 rdsysinfo 錯誤",
        "facts": [
            f"Posttest 的 Invoke-Profile 結果是 FAIL、return code 500003；13 個指令中只有 Get-SystemEventsDiagnostics 失敗（Posttest/Summary-Invoke-Profile.log）。",
            f"失敗行為 {C('SuspectedEventsFound | * FAIL * | 3')}（Debug-Get-WindowsSystemEventDiagnostics.log 第 47 行）。",
            f"這 3 筆 suspected events 都是 System log、Event ID 7000，訊息為「rdsysinfo service failed to start … A required certificate is not within its validity period …」，時間 {'、'.join(t7000_post)}（AllSuspectedEvents.log）。",
            f"同一份 System log 的 Event 7045 顯示服務檔路徑為 {DRV}，在 SDK 工具包資料夾內。",
            f"這 3 筆事件時間{'都' if inside(t7000_post, pcw) else '並非都'}落在 Invoke-PcietoolChecks 的執行區間 {pcw[0]}–{pcw[1]} 內。",
            f"Pretest 的 System log 也有 {len(t7000_pre)} 筆同樣的 Event 7000（{'、'.join(t7000_pre)}），{'都' if inside(t7000_pre, pcw_pre) else '並非都'}落在當時 Invoke-PcietoolChecks 的區間 {pcw_pre[0]}–{pcw_pre[1]} 內；Pretest 的指令清單沒有 Get-SystemEventsDiagnostics，所以沒有被判定。",
            "排除清單檔載入的 pattern 數為 2（Summary-Get-SystemEventsDiagnostics.log 第 53 行），3 筆事件仍被列為 suspected。"],
        "infer": [], "unknown": [
            "憑證的名稱、簽署者與到期日：log 沒有記錄，無法確認是哪個憑證過期。",
            "驅動載入失敗是否影響 pcietool 的輸出：log 只顯示 Invoke-PcietoolChecks 判 PASS，沒有進一步資訊。",
            "排除清單 2 個 pattern 的內容：log 只給數量，沒有列出內容。"],
        "ev": [ev(slot, "Posttest/Summary-Invoke-Profile.log", r"Get-SystemEventsDiagnostics|FINAL RESULT|Invoke-PcietoolChecks|return code", n=10),
               ev(slot, "Posttest/Get-SystemEventsDiagnostics/Debug-Get-WindowsSystemEventDiagnostics.log", rng=(44, 48)),
               ev(slot, "Posttest/Get-SystemEventsDiagnostics/Summary-Get-SystemEventsDiagnostics.log", r"Exclude Patterns|Suspected Events Found", n=4),
               ev(slot, "Posttest/Get-SystemEventsDiagnostics/AllSuspectedEvents.log", n=12),
               ev(slot, "Posttest/Get-SystemEventsDiagnostics/eventsLog-System-2*.log", r"rdsysinfo", n=24),
               ev(slot, "Pretest/Export-WindowsSystemEvents/eventsLog-System-2*.log", r"Event ID: 7000.*rdsysinfo", n=6)]})

    # 2. memory CPER (only if present)
    if mem:
        m = mem[0]
        d = m["data"]
        F.append({"sev": "warn", "conf": "已確認", "where": "CPER 記憶體", "title": f"Pretest 有 {len(mem)} 筆 Corrected 記憶體 CPER",
            "facts": [
                f"{m['rel']}：TimeStamp 2026-10-30T{m['ts']}、Severity {m['sev']}、description {C(m['desc'])}、FRUText {C(m['fru'])}。",
                f"欄位：module {d['module']}、bank {d['bank']}、row {d['row']}、column {d['column']}、phy_address {C(hex(d['phy_address']))}、error_type {d['error_type']}；Flags 中 ThresholdExceeded = {m['thr']}。",
                f"時間早於 AC cycle 開始（nodestatus 紀錄 12:28:42）。",
                f"其餘 {len(cp)-1} 筆 CPER 都是 {C('ACPI_ERROR_TYPE_VENDOR_ACCELERATOR')}，沒有第二筆記憶體型態。",
                f"這個 zip 的 Pretest/cper 資料夾編號從 CPER_{min(c['n'] for c in cp)} 開始（沒有 CPER_1、CPER_2）。"],
            "infer": [], "unknown": [
                "這筆記憶體錯誤對應哪一條 DIMM：CPER 內只有 module/bank/row/column 數值，沒有 DIMM 槽位名稱。",
                "是否曾在更早的開機重複出現：zip 內沒有 04:16 之前的紀錄，CPER_1、CPER_2 也不在 zip 內。",
                "04:16:31 當時系統的狀態：log 沒有該時段的 System log。"],
            "ev": [ev(slot, m["rel"], n=140), ev_text(f"[{L}] Pretest/cper 內的檔案清單", [os.path.basename(p) for p in sorted(glob.glob(os.path.join(E.ROOTS[slot], "Pretest", "cper", "*")))]),
                   ev(slot, "nodestatus/*.jsonl", r"down_start_utc", n=2)]})

    # 3. accelerator CPER
    acc_lines = [f"CPER_{c['n']}（{c['phase']}）{c['ts']}　DID 0x{c['did']:04X}　Bus 0x{c['bus']:02X}" for c in acc]
    F.append({"sev": "warn", "conf": "已確認", "where": "CPER", "title": f"{len(acc)} 筆 Corrected 加速器 CPER（sdm_interrupt_events）",
        "facts": [
            f"{len(acc)} 筆 CPER 全部是 Severity Corrected、description {C('ACPI_ERROR_TYPE_VENDOR_ACCELERATOR')}、FRUText {C(acc[0]['fru'])}，VID 0x1414。每筆 {C('sdm_interrupt_events')} = {acc[0]['sdm']}（0x{acc[0]['sdm']:X}）。",
            "逐筆：" + "；".join(acc_lines) + "。",
            f"每筆的其餘欄位（*_ecc_error.*、co_proc_*、sdm_wdt_error、fab_wdt_error 等）非零個數：{sum(len(c['nz']) for c in acc)}。",
            f"NTTTCP 執行區間 {stress[0][11:]}–{stress[1][11:]} 內的 CPER 筆數：{len(during)}。",
            f"Pretest 的 CPER {', '.join(c['ts'] for c in pre_acc)} 中，有 {len(pairs)} 筆在 System log 的 Event 6008（上次關機為非預期）之前："
            + "；".join(f"CPER {a} → 6008 {b}（相差 {d} 秒）" for a, b, d in pairs) + "。",
            f"其餘 Pretest CPER 的時間在 Write-Config 執行區間 {wc_pre[0]}–{wc_pre[1]} 內者：{', '.join(c['ts'] for c in pre_acc if wc_pre[0] <= c['ts'] <= wc_pre[1]) or '無'}；Posttest CPER {', '.join(c['ts'] for c in post_acc)} 在 Write-Config 區間 {wc_post[0]}–{wc_post[1]} 內：{'是' if all(wc_post[0] <= c['ts'] <= wc_post[1] for c in post_acc) else '否'}。"],
        "infer": [], "unknown": [
            f"{C('sdm_interrupt_events')} 位元的意義，以及這是否為已知的良性事件：log 沒有說明。",
            "CPER 與 Event 6008、Write-Config 在時間上接近，但 log 沒有顯示兩者之間有因果關係。",
            "為何有些 CPER 的 DID 是 0xC010、有些是 0xC011：log 沒有說明。"],
        "ev": [ev(slot, c["rel"], r'"(Severity|TimeStamp|FRUText|description|device_id|bus_number|sdm_interrupt_events)"', n=9) for c in acc[:4]] +
              [ev_text(f"[{L}] 其餘 {max(0, len(acc)-4)} 筆 CPER 摘要（欄位同上，原始檔請見 evidence 資料夾 cper/）", acc_lines[4:])] +
              [ev(slot, "Pretest/Export-WindowsSystemEvents/eventsLog-System-2*.log", r"Event ID: 6008", n=6, maxlen=300),
               ev(slot, "Pretest/Summary-Invoke-Profile.log", r"Write-Config", n=3), ev(slot, "Posttest/Summary-Invoke-Profile.log", r"Write-Config", n=3)]})

    # 4. I2C
    def fmt_rng(xs):
        return f"{len(xs)} 筆" + (f"，rec_fail_cnt {min(cnts(xs))}→{max(cnts(xs))}" if xs and "rec_fail_cnt" in xs[0][1] else "")
    F.append({"sev": "warn", "conf": "已確認", "where": "BMC", "title": "BMC journal 的 I2C 訊息（bus11 hung、bus7 contention）",
        "facts": [
            f"Pretest journal：I2C bus11「recovery did not complete, bus still hung」{fmt_rng(hung)}（{hung[0][1][:15] if hung else ''}–{hung[-1][1][:15] if hung else ''}）。" if hung else "Pretest journal 沒有 bus11 的 hung 訊息。",
            f"Pretest journal：I2C bus7「Suppress … recovery SEL: multi-master contention」{len(sup_pre)} 筆。",
            f"Posttest journal（擷取範圍 {i2c_post[0][1][:15]} 起的最後 2 小時）：I2C bus7 訊息共 {len(sup_post)} 筆，其中「recovery-fail」{len(rf_post)} 筆、rec_fail_cnt {min(cnts(rf_post))}→{max(cnts(rf_post))}，其餘為「recovery SEL」；bus11 訊息 {len([x for x in other_i2c_post])} 筆。",
            f"訊息字面都是 Suppress（BMC 抑制）；兩個階段的 SEL 都只有 1 筆「Log area reset/cleared」（{sel_t}），沒有 I2C 相關 SEL 紀錄。"],
        "infer": [], "unknown": [
            "bus11、bus7 各接哪些裝置，以及對功能的影響：log 沒有說明。",
            "bus11 之後是否恢復：Pretest 最後一筆之後沒有更多 bus11 訊息，但 Posttest 的 journal 只涵蓋最後 2 小時，無法涵蓋中間時段。",
            "rec_fail_cnt 的計數方式：log 只給數值。"],
        "ev": [ev(slot, "Pretest/bmcclishell/bmc-journal-last-2h.log", r"I2C bus\d+", n=12, maxlen=300), ev(slot, "Posttest/bmcclishell/bmc-journal-last-2h.log", r"I2C bus\d+", n=20, maxlen=300),
               ev(slot, "Posttest/rackscm_sel_decode/selRecords.txt", n=4)]})

    # 5. OL_S1 temp
    st = sm["OL_S1_SOC_TMP"]
    F.append({"sev": "info", "conf": "已確認", "where": "感測器", "title": f"OL_S1_SOC_TMP：最高 {st['max']:.1f} °C，並有 {len(miss)} 個輪詢時間點沒有讀值",
        "facts": [
            f"OL_S1_SOC_TMP 共 {st['n']} 筆，最小 {st['min']:.1f}、平均 {st['avg']:.1f}、最高 {st['max']:.1f} °C。最高值出現在 {olmax_blocks[0][2][11:19]}（原始檔第 {olmax_blocks[0][3]} 行起）。",
            f"同一份監控中 NODE_PWR 有 {len(polls)} 個輪詢時間點，OL_S1_SOC_TMP 少了 {len(miss)} 個。缺少的時間點列於原始資料。"],
        "infer": [], "unknown": [
            "這個感測器的警告／關機門檻：log 內沒有，因此無法判斷這個溫度是否偏高。",
            "缺少讀值的原因：log 沒有說明。"], "ev": ol_ev})

    # 6. NTTTCP counters
    retx_s = sx["packets_retransmitted"] / sx["packets_sent"] * 100
    F.append({"sev": "info", "conf": "已確認", "where": "Stress", "title": "NTTTCP errors 與重傳計數",
        "facts": [
            f"sender.xml：errors {sx['errors']:.0f}、packets_retransmitted {sx['packets_retransmitted']:,.0f}／packets_sent {sx['packets_sent']:,.0f}（{retx_s:.3f}%）。",
            f"receiver.xml：errors {rx['errors']:.0f}、packets_retransmitted {rx['packets_retransmitted']:,.0f}／packets_sent {rx['packets_sent']:,.0f}（{rx['packets_retransmitted']/rx['packets_sent']*100:.3f}%）。",
            f"done.json：status {done['status']}、exit_code {done['exit_code']}。"],
        "infer": [], "unknown": [
            "errors 72 的定義，以及多少算可接受：log 沒有判定基準。",
            "是否與其他機器相比偏高：本次只有兩台的資料；兩台的 errors 都是 72。"],
        "ev": [ev(slot, "Stress/Net_stress/sender.xml", r"<(total_bytes|realtime|throughput metric=\"mbps\"|packets_|errors|cpu)", after_last=r"</thread>"),
               ev(slot, "Stress/Net_stress/receiver.xml", r"<(total_bytes|realtime|throughput metric=\"mbps\"|packets_|errors|cpu)", after_last=r"</thread>"),
               ev(slot, "Stress/Net_stress/done.json")]})
    if meta.get("np_note"):
        F.append({"sev": "info", "conf": "已確認", "where": "Stress", "title": "receiver.xml 的 num_processors 為 4",
            "facts": [f"sender.xml：num_processors {sx['num_processors']:.0f}、cpu {sx['cpu']}%；receiver.xml：num_processors {rx['num_processors']:.0f}、cpu {rx['cpu']}%。",
                      "另一台 Slot2 的 sender / receiver 都是 64。", "本機 sender.xml 的 num_processors 是 64。"],
            "infer": [], "unknown": ["為何同一台機器的 receiver 記錄為 4：log 沒有說明。", "對結果的影響：該方向的吞吐量與對端 sender 的差距為 +0.0008%，未見差異。"],
            "ev": [ev(slot, "Stress/Net_stress/receiver.xml", r"<(num_processors|cpu)", after_last=r"</thread>"), ev(slot, "Stress/Net_stress/sender.xml", r"<(num_processors|cpu)", after_last=r"</thread>")]})

    # 7. BladeSku
    F.append({"sev": "info", "conf": "已確認", "where": "Pre = Post", "title": "BladeSkuCheck 報告內的錯誤與警告",
        "facts": [
            f"BladeSkuCheck.report.txt 有 {n_blade} 行 Error / Warning（MissionModeOperator、HspToolOperator、BmcOperator 失敗；CPLD 讀取 completion code FF；PhysicalPresenceVersionInfo 控制字元替換）。",
            f"Pretest 與 Posttest 的報告檔{'逐位元組相同' if blade_same else '內容不同'}；Invoke-BladeSkuChecks 兩次都判 PASS。",
            (f"BMC journal（Posttest）有 {n_cpld} 行提到 HPM_CPLD2 / GLOBAL_CPLD 的 dbus 錯誤（原始資料列出前 4 行；僅並列，不做因果判斷）。" if n_cpld else "BMC journal（Pretest、Posttest）沒有提到 HPM_CPLD2 / GLOBAL_CPLD（grep 結果 0 行）。")],
        "infer": [], "unknown": ["這些 operator 失敗的原因：報告只有 exit code 與錯誤字串。"] + (["與 BMC journal 的 dbus 訊息是否有關：log 沒有說明。"] if n_cpld else []),
        "ev": [ev(slot, "Posttest/bladeskucheck/BladeSkuCheck.report.txt", r"^(Error|Warning)", n=30, maxlen=300),
               ev(slot, "Posttest/bmcclishell/bmc-journal-last-2h.log", r"HPM_CPLD2|GLOBAL_CPLD", n=4, maxlen=300)]})

    # 8. CSIDiag
    F.append({"sev": "info", "conf": "已確認", "where": "Pre = Post", "title": "CSIDiag WARN 與 CSI_DER 錯誤條目",
        "facts": [
            f"Invoke-CsiDiagChecks 兩次都是 PASS，但內含 {C('CSIDiag-Execution | * WARN * | … non-zero exit code: -855034864')}。",
            f"Posttest CSI_DER.log：CSI_ERR {n_err} 筆（{C('DISK_ER_CDF28')}，eDrive PSID Revert and Activate：eDrive in incorrect band capabiltiies state）、CSI_MODU_ERR {n_modu} 筆、CSI_INFO {n_info} 筆。",
            f"Pretest 與 Posttest 的條目{'（去除時間戳後）完全相同' if der_same else '不相同'}。",
            f"{n_err} 筆 CSI_ERR 的型號字串都是 MZCL93T8HFLB（storagetool-disk-inventory 內共有 14 顆該型號）。",
            "Sel_Heartbeat.json 在 Pretest 與 Posttest 都記錄 SelHeartbeatStatus Fail、Severity ERR（IpmiUtil exit code 0x7fffffff）；同一個 Posttest 的 ipmiutil sel -r 另外成功完成（Sel_RAW.log）。",
            "Pretest 另有 ipmiutil sel -r 逾時 60 秒的 FAIL 行；Posttest 沒有。"],
        "infer": [], "unknown": ["eDrive 狀態是否為預期：log 沒有說明。", "為何只有 7 筆（inventory 有 14 顆同型號）：log 沒有說明。"],
        "ev": [ev(slot, "Posttest/csidiag/Summary-Invoke-CsiDiagChecks.log", r"WARN|FAIL|FINAL", n=6), ev(slot, "Pretest/csidiag/Summary-Invoke-CsiDiagChecks.log", r"WARN|FAIL|FINAL", n=6),
               ev(slot, "Posttest/csidiag/CSI_DER.log", r"CSI_(ERR|MODU_ERR|INFO)", n=40, maxlen=300), ev(slot, "Posttest/csidiag/Sel_Heartbeat.json"), ev(slot, "Pretest/csidiag/Sel_Heartbeat.json"),
               ev(slot, "Posttest/csidiag/Sel_RAW.log", r"ipmiutil sel|SEL Ver|completed", n=4),
               ev(slot, "Posttest/storagetool/storagetool-disk-inventory.log", r"Disk#", n=17, maxlen=140)]})

    # 9. nothing found
    pcie_ev = [ev(slot, "Posttest/pcietool/pcie--linkstatus.txt", r"^BDF", n=4, maxlen=160),
               ev_text(f"[{L}] pcie--linkstatus.txt 比對（程式計算）", [f"Posttest 共 {ndev} 個 BDF 裝置；Cur 與 Max 不同的裝置數：{nbad}。", f"Pretest 與 Posttest 檔案內容{'完全相同' if same else '不同'}。"])]
    F.append({"sev": "ok", "conf": "已確認", "where": "", "title": "SEL、WHEA、crash dump、PCIe、SMART 沒有找到異常紀錄",
        "facts": [
            f"BMC SEL：Pretest 與 Posttest 都只有 1 筆「Log area reset/cleared」（{sel_t}）；ipmiutil 顯示 Used=1（Sel_RAW.log）。",
            f"WHEA 事件檔：Pretest 與 Posttest 都是 0 bytes；crashdumps 的 DumpFilesRenamed、DumpFilesRenameFailed 皆為 0；system dump entries 的 Members@odata.count 為 0。",
            f"PCIe：{ndev} 個裝置的目前速度／寬度都等於最大值，前後{'完全相同' if same else '不同'}。",
            f"SMART（15 顆實體 NVMe，Disk#15 為虛擬磁碟）：Media Error Count{'全為 0' if not sissue else ' 有非零'}；其餘欄位見原始資料（Pretest → Posttest）。",
            f"AC cycle：nodestatus 記錄停機 550 秒、status success。",
            "溫度、電壓、功耗只列出數值（見感測器區），log 沒有提供門檻，因此不對這些數值做正常／異常判定。"],
        "infer": [], "unknown": ["這些只代表「在這份 log 的範圍內沒有紀錄」，不代表硬體沒有問題。"],
        "ev": [ev(slot, "Posttest/rackscm_sel_decode/selRecords.txt", n=4), ev(slot, "Pretest/rackscm_sel_decode/selRecords.txt", n=4), ev(slot, "Posttest/csidiag/Sel_RAW.log", r"SEL Ver", n=2),
               ev_text(f"[{L}] WHEA 事件檔大小", [f"{ph}/…/{os.path.basename(p)} = {os.path.getsize(p)} bytes" for ph in ("Pretest", "Posttest") for p in glob.glob(os.path.join(E.ROOTS[slot], ph, "*", "eventsLog-System-WHEA-*.log"))]),
               ev(slot, "Posttest/crashdumps/test-metrics-Posttest.json"), ev(slot, "Posttest/systemdumpentries/01_capturesystemdumpentries.log", r"Members", n=3),
               ev(slot, "nodestatus/*.jsonl", n=3, maxlen=300)] + pcie_ev + [ev_text(f"[{L}] SMART 逐顆（程式計算，來源 smartctl/summary-*.json）", srows)]})

    # ----- kpis, timeline, checks -----
    tx_g, rx_g = meta["tx"], meta["rx"]
    kpis = [
        {"k": "TX 吞吐量", "v": f"{tx_g:.1f}", "u": "Gbps", "d": f"sender.xml，送往 {meta['peer']}"},
        {"k": "RX 吞吐量", "v": f"{rx_g:.1f}", "u": "Gbps", "d": f"receiver.xml，來自 {meta['peer']}"},
        {"k": "TX + RX", "v": f"{tx_g+rx_g:.1f}", "u": "Gbps", "d": "兩個數字相加"},
        {"k": "重傳比例", "v": f"{retx_s:.2f}", "u": "%", "d": f"{sx['packets_retransmitted']:,.0f} / {sx['packets_sent']:,.0f} packets"},
        {"k": "NTTTCP errors", "v": f"{sx['errors']:.0f}", "u": "", "d": f"done.json：{done['status']}，exit {done['exit_code']}"},
        {"k": "SEL 紀錄數", "v": "1", "u": "筆", "d": "Log area reset/cleared（前後相同）"},
    ]
    ok = ["ok", "PASS"]
    ptxt = lambda w: f"{w[0]}–{w[1]}"
    checks = [
        {"name": "Write-Config", "pre": ok, "post": ok, "note": f"Pretest {ptxt(wc_pre)}、Posttest {ptxt(wc_post)}"},
        {"name": "Invoke-SmartCtlChecks", "pre": ok, "post": ok, "note": "詳見「未找到異常紀錄」的原始資料"},
        {"name": "Invoke-StorageToolChecks", "pre": ok, "post": ok, "note": ""},
        {"name": "Invoke-BladeSkuChecks", "pre": ok, "post": ok, "note": f"報告前後{'相同' if blade_same else '不同'}；內含 {n_blade} 行 Error/Warning"},
        {"name": "Invoke-CsiDiagChecks", "pre": ["warn", "PASS · WARN"], "post": ["warn", "PASS · WARN"], "note": f"CSI_DER 條目前後{'相同' if der_same else '不同'}；Pretest 另有 ipmiutil sel -r 逾時"},
        {"name": "Invoke-CerberusUtilityChecks", "pre": ok, "post": ok, "note": ""},
        {"name": "Invoke-IpmitoolChecks", "pre": ok, "post": ok, "note": ""},
        {"name": "Invoke-IpmiutilChecks", "pre": ok, "post": ok, "note": ""},
        {"name": "Invoke-PcietoolChecks", "pre": ok, "post": ok, "note": f"Pretest {ptxt(pcw_pre)}、Posttest {ptxt(pcw)}；rdsysinfo Event 7000 發生於此區間"},
        {"name": "Invoke-IpconfigChecks", "pre": ok, "post": ok, "note": ""},
        {"name": "Invoke-RdbdatChecks", "pre": ok, "post": ok, "note": ""},
        {"name": "Export-WindowsSystemEvents", "pre": ok, "post": None, "note": f"Pretest 的 System log 有 {len(t7000_pre)} 筆 rdsysinfo Event 7000"},
        {"name": "Export-BMCSel", "pre": ok, "post": None, "note": ""},
        {"name": "Get-SystemEventsDiagnostics", "pre": None, "post": ["bad", "FAIL 500003"], "note": "SuspectedEventsFound = 3"},
        {"name": "Clear-SystemEvents", "pre": ok, "post": ok, "note": ""},
        {"name": "整體結果", "pre": ok, "post": ["bad", "FAIL"], "note": f"Pretest {meta['pre_dur']}、Posttest {meta['post_dur']}"},
    ]
    tl = []
    if mem:
        tl.append({"t": mem[0]["ts"], "s": "warn", "title": "Corrected 記憶體 CPER", "d": f"CPER_{mem[0]['n']}，早於 AC cycle"})
    tl += [{"t": "12:28:42", "s": "info", "title": "AC cycle 開始", "d": "nodestatus jsonl"},
           {"t": "12:37:52", "s": "ok", "title": "主機恢復上線", "d": "停機 550 秒，status success"},
           {"t": "12:38:26", "s": "info", "title": "背景感測器監控啟動", "d": "monitor_lifecycle.log"},
           {"t": pre_w["Write-Config"][0], "s": "ok", "title": "Pretest 開始", "d": f"PASS，耗時 {meta['pre_dur']}"}]
    for c in pre_acc:
        pass
    tl += [{"t": "13:10:11", "s": "info", "title": "OS 設定（MTU 9014、High performance）", "d": f"os_config.log，至 {osc_end}"},
           {"t": stress[0][11:], "s": "ok", "title": "NTTTCP 開始（推算）", "d": "由 done.json 時間減 21,600 秒推算，log 沒有開始時間"},
           {"t": done_t, "s": "ok", "title": "NTTTCP 完成", "d": f"done.json：{done['status']}，exit {done['exit_code']}"},
           {"t": post_w["Write-Config"][0], "s": "info", "title": "Posttest 開始", "d": f"Write-Config 期間 CPER {', '.join(c['ts'] for c in post_acc)}"},
           {"t": t7000_post[0], "s": "bad", "title": f"rdsysinfo Event 7000 ×{len(t7000_post)}", "d": "、".join(t7000_post)},
           {"t": post_w["Get-SystemEventsDiagnostics"][1], "s": "bad", "title": "Posttest FAIL 500003", "d": f"耗時 {meta['post_dur']}"},
           {"t": "19:35:19", "s": "info", "title": "背景監控停止", "d": "monitor_lifecycle.log"}]
    tl.sort(key=lambda x: x["t"])

    return {
        "title": meta["title"], "ids": meta["ids"], "vers": VERS,
        "verdict": [{"k": "Stress · NTTTCP", "s": "ok", "st": "完成", "d": f"done.json：{done['status']}，exit {done['exit_code']}；21,600 秒"},
                    {"k": "Pretest", "s": "ok", "st": "PASS", "d": f"return code 0，耗時 {meta['pre_dur']}"},
                    {"k": "Posttest", "s": "bad", "st": "FAIL 500003", "d": f"Get-SystemEventsDiagnostics 判出 {len(t7000_post)} 筆 rdsysinfo Event 7000"}],
        "window": meta["window"], "stress": {"start": stress[0], "end": stress[1]},
        "threads": {"tx": threads(meta["csv_tx"]), "rx": threads(meta["csv_rx"])},
        "totals": {"tx": {"gbps": tx_g, "mb": meta["tx_mb"]}, "rx": {"gbps": rx_g, "mb": meta["rx_mb"]}},
        "kpis": kpis, "findings": F, "timeline": tl, "checks": checks, "key": key,
        "series": {k["name"]: sj["series"][k["name"]] for k in key}, "stats": sj["stats"],
        "statsMap": {k["name"]: sm[k["name"]] for k in key}, "nmax": nmax,
        "_facts": {"t7000_pre": t7000_pre, "t7000_post": t7000_post, "cper_n": len(cp), "mem": len(mem), "acc": len(acc), "hung": len(hung), "sup_pre": len(sup_pre), "sup_post": len(sup_post),
                   "miss": len(miss), "olmax": olmax, "gap": gap, "osc_end": osc_end, "done_t": done_t, "sx": sx, "rx": rx, "blade_same": blade_same, "der_same": der_same, "pairs": pairs,
                   "during": len(during), "sm": sm, "nmax": nmax, "same": same, "ndev": ndev, "sissue": sissue},
    }


VERS = [["BIOS", "C4143.BS.0514.AC.01.02"], ["BMC", "M1120-C4143.OBMC.26.7.27-3"], ["SDK", "8.2.3.197"]]
s2 = build_slot("s2", {"title": "C4143-Scale Rack05 OU02 Slot2", "sens": "sensors.json", "stress": ("2026-10-30T13:11:36", "2026-10-30T19:11:36"), "tx": 257.937, "rx": 262.585, "peer": "192.9.35.46",
                        "ids": [["Host", "C41-SCALE-R5-S2"], ["IP", "192.9.35.2（對端 .46）"], ["Run", "20261030_122641"]], "window": {"start": "2026-10-30T12:39:20", "end": "2026-10-30T19:35:19"},
                        "csv_tx": "sender_threads.csv", "csv_rx": "receiver_threads.csv", "tx_mb": 664168438.5, "rx_mb": 676135429.336, "pre_dur": "09:33", "post_dur": "08:25"})
s46 = build_slot("s46", {"title": "C4143-Scale Rack05 OU02 Slot46", "sens": "sensors46.json", "stress": ("2026-10-30T13:11:34", "2026-10-30T19:11:34"), "tx": 262.588, "rx": 257.940, "peer": "192.9.35.2",
                          "ids": [["Host", "C4-SCALE-R5-S46"], ["IP", "192.9.35.46（對端 .2）"], ["Run", "20261030_122641"]], "window": {"start": "2026-10-30T12:42:21", "end": "2026-10-30T19:34:38"},
                          "csv_tx": "sender46_threads.csv", "csv_rx": "receiver46_threads.csv", "tx_mb": 676142462.25, "rx_mb": 664174275.582, "pre_dur": "09:35", "post_dur": "08:15", "np_note": True})

# ------------------------------------------------------------------ compare
raw = {"s2": {"tx": 257937.413, "rx": 262584.730, "txMB": 664168438.5, "rxMB": 676135429.336},
       "s46": {"tx": 262587.585, "rx": 257939.591, "txMB": 676142462.25, "rxMB": 664174275.582}}
cross = [{"dir": "Slot2 → Slot46", "tx": raw["s2"]["tx"], "rx": raw["s46"]["rx"], "txMB": raw["s2"]["txMB"], "rxMB": raw["s46"]["rxMB"]},
         {"dir": "Slot46 → Slot2", "tx": raw["s46"]["tx"], "rx": raw["s2"]["rx"], "txMB": raw["s46"]["txMB"], "rxMB": raw["s2"]["rxMB"]}]
for r in cross:
    r["diffPct"] = (r["rx"] - r["tx"]) / r["tx"] * 100

f2, f46 = s2["_facts"], s46["_facts"]
sm2, sm46 = f2["sm"], f46["sm"]


def row(k, a, b, note="", mono=True, diff=None):
    return {"k": k, "a": str(a), "b": str(b), "note": note, "mono": mono, "diff": (str(a) != str(b)) if diff is None else diff}


cmd2 = lambda s: E.lines(s, "Stress/Net_stress/ntttcp_sender_cmd.txt")[1][0]
rows = [
    {"grp": "身分"},
    row("主機名稱", "C41-SCALE-R5-S2", "C4-SCALE-R5-S46", "", diff=False),
    row("IP", "192.9.35.2", "192.9.35.46", "", diff=False),
    {"grp": "NTTTCP（sender.xml / receiver.xml）"},
    row("TX（Gbps）", f"{raw['s2']['tx']/1000:.3f}", f"{raw['s46']['tx']/1000:.3f}", "互為對端，見上方交叉驗證", diff=False),
    row("RX（Gbps）", f"{raw['s2']['rx']/1000:.3f}", f"{raw['s46']['rx']/1000:.3f}", "", diff=False),
    row("done.json 時間（UTC）", f2["done_t"], f46["done_t"], "", diff=False),
    row("packets_retransmitted（sender）", f"{f2['sx']['packets_retransmitted']:,.0f}", f"{f46['sx']['packets_retransmitted']:,.0f}", "", diff=False),
    row("errors（sender / receiver）", f"{f2['sx']['errors']:.0f} / {f2['rx']['errors']:.0f}", f"{f46['sx']['errors']:.0f} / {f46['rx']['errors']:.0f}"),
    row("num_processors（sender / receiver）", f"{f2['sx']['num_processors']:.0f} / {f2['rx']['num_processors']:.0f}", f"{f46['sx']['num_processors']:.0f} / {f46['rx']['num_processors']:.0f}"),
    row("cpu%（sender / receiver）", f"{f2['sx']['cpu']} / {f2['rx']['cpu']}", f"{f46['sx']['cpu']} / {f46['rx']['cpu']}"),
    {"grp": "Pretest / Posttest"},
    row("Pretest", "PASS · 09:33", "PASS · 09:35", "", diff=False),
    row("Posttest", "FAIL 500003 · 08:25", "FAIL 500003 · 08:15", "", diff=False),
    row("rdsysinfo Event 7000（Pretest / Posttest）", f"{len(f2['t7000_pre'])} / {len(f2['t7000_post'])}", f"{len(f46['t7000_pre'])} / {len(f46['t7000_post'])}"),
    row("BladeSkuCheck 報告前後相同", "是" if f2["blade_same"] else "否", "是" if f46["blade_same"] else "否", "", diff=False),
    row("CSI_DER 條目前後相同", "是" if f2["der_same"] else "否", "是" if f46["der_same"] else "否", "", diff=False),
    {"grp": "事件紀錄"},
    row("Corrected CPER 總數", f2["cper_n"], f46["cper_n"], "", diff=False),
    row("其中記憶體型態", f2["mem"], f46["mem"]),
    row("其中加速器型態", f2["acc"], f46["acc"], "", diff=f2["acc"] != f46["acc"]),
    row("NTTTCP 區間內新增 CPER", f2["during"], f46["during"], "", diff=False),
    row("I2C bus11 hung 訊息（Pretest）", f2["hung"], f46["hung"]),
    row("I2C bus7 suppress 訊息（Pretest / Posttest）", f"{f2['sup_pre']} / {f2['sup_post']}", f"{f46['sup_pre']} / {f46['sup_post']}"),
    row("SEL 紀錄數", "1", "1", "", diff=False),
    row("PCIe 前後相同 / 降速裝置", f"{'是' if f2['same'] else '否'} / 0", f"{'是' if f46['same'] else '否'} / 0", "", diff=False),
    {"grp": "感測器（OOB 監控，只列數值）"},
    row("NODE_PWR 取樣筆數", sm2["NODE_PWR"]["n"], sm46["NODE_PWR"]["n"], "兩台的起訖時間不同"),
    row("SoC 最高溫（°C）", sm2["SOC_TMP_MAX"]["max"], sm46["SOC_TMP_MAX"]["max"]),
    row("DIMM 最高溫（°C）", sm2["DIMM_TMP_MAX"]["max"], sm46["DIMM_TMP_MAX"]["max"]),
    row("OL_S1_SOC_TMP 最高（°C）", sm2["OL_S1_SOC_TMP"]["max"], sm46["OL_S1_SOC_TMP"]["max"], "log 沒有門檻值"),
    row("OL_S1_SOC_TMP 缺少讀值", f2["miss"], f46["miss"]),
    row("進風溫度最高（°C）", sm2["NODE_INLET_TMP"]["max"], sm46["NODE_INLET_TMP"]["max"], "", diff=False),
    row("Node 功耗 平均 / 最高（W）", f"{sm2['NODE_PWR']['avg']:.1f} / {sm2['NODE_PWR']['max']:.0f}", f"{sm46['NODE_PWR']['avg']:.1f} / {sm46['NODE_PWR']['max']:.0f}"),
]

xml_ev = []
for s in ("s2", "s46"):
    for nm in ("sender", "receiver"):
        xml_ev.append(ev(s, f"Stress/Net_stress/{nm}.xml", r"<(total_bytes|realtime|throughput metric=\"mbps\"|packets_sent|packets_received)", after_last=r"</thread>"))
dup_ev = []
for s in ("s2", "s46"):
    dup_ev += [ev(s, "Stress/Net_stress/ntttcp_sender_cmd.txt", maxlen=300), ev(s, "Stress/Net_stress/ntttcp_receiver_cmd.txt", maxlen=300),
               ev(s, "Stress/Net_stress/os_config.log", r"Complete|Start", n=2), ev(s, "Stress/Net_stress/done.json")]
fail_ev = [ev(s, "Posttest/Summary-Invoke-Profile.log", r"Get-SystemEventsDiagnostics|FINAL RESULT|SDK Version", n=6) for s in ("s2", "s46")] + \
          [ev(s, "Posttest/Get-SystemEventsDiagnostics/AllSuspectedEvents.log", n=12) for s in ("s2", "s46")]

compare = {
    "title": "Rack05 OU02 · Slot2 ⇄ Slot46",
    "ids": [["Run", "20261030_122641"], ["RSCM", "192.9.35.52"], ["對端", "192.9.35.2 ⇄ 192.9.35.46"], ["SDK", "8.2.3.197"]],
    "vers": [["BIOS", "C4143.BS.0514.AC.01.02"], ["BMC", "M1120-C4143.OBMC.26.7.27-3"], ["兩台版本", "相同（ipmitool 結果）"]],
    "verdict": [{"k": "Stress · NTTTCP", "s": "ok", "st": "兩端吻合", "d": f"發送與接收差距 {abs(cross[0]['diffPct']):.4f}% / {abs(cross[1]['diffPct']):.4f}%"},
                {"k": "Pretest · 兩台", "s": "ok", "st": "PASS / PASS", "d": "Slot2 09:33、Slot46 09:35"},
                {"k": "Posttest · 兩台", "s": "bad", "st": "FAIL / FAIL", "d": "兩台都是 Get-SystemEventsDiagnostics，SuspectedEventsFound = 3"}],
    "cross": cross, "rows": rows,
    "findings": [
        {"sev": "ok", "conf": "已確認", "title": "兩端的 NTTTCP 數字互相吻合",
         "facts": [f"Slot2 sender {raw['s2']['tx']:,.1f} Mbps ↔ Slot46 receiver {raw['s46']['rx']:,.1f} Mbps（{cross[0]['diffPct']:+.4f}%）。",
                   f"Slot46 sender {raw['s46']['tx']:,.1f} Mbps ↔ Slot2 receiver {raw['s2']['rx']:,.1f} Mbps（{cross[1]['diffPct']:+.4f}%）。",
                   f"總傳輸量（MB）：Slot2 送 {raw['s2']['txMB']:,.0f}／Slot46 收 {raw['s46']['rxMB']:,.0f}；Slot46 送 {raw['s46']['txMB']:,.0f}／Slot2 收 {raw['s2']['rxMB']:,.0f}。"],
         "infer": [], "unknown": ["差距的來源（例如計時起訖點不同）：log 沒有說明。"], "ev": xml_ev},
        {"sev": "ok", "conf": "含推論", "title": "兩個方向是同時進行的（全雙工）",
         "facts": ["兩台各自有 sender 與 receiver 兩條指令，參數都是 " + C("-t 21600") + "（見原始資料）。",
                   "四份 XML 的 realtime 都約為 21,600 秒（21600.002～21600.019）。",
                   f"os_config.log 最後一行時間 {f2['osc_end']}（兩台相同），done.json 時間 Slot2 {f2['done_t']}、Slot46 {f46['done_t']}。兩者相隔約 {f2['gap']:,} 秒。"],
         "infer": [f"若兩個方向是先後執行，至少需要 2 × 21,600 = 43,200 秒；但從 OS 設定完成到 done.json 只有約 {f2['gap']:,} 秒，所以兩個方向必須有重疊（依據：os_config.log 與 done.json 的時間，並假設兩者都是 UTC）。"],
         "unknown": ["XML 與 cmd 檔沒有各方向的開始／結束時間戳，無法逐秒證明兩個方向的重疊程度。", "兩個 log 的時區是否都是 UTC：done.json 標示 +00:00，os_config.log 沒有標示（System log 顯示 time zone bias 為 0）。"], "ev": dup_ev},
        {"sev": "bad", "conf": "已確認", "title": "兩台 Posttest 失敗的記錄相同",
         "facts": ["兩台都是 return code 500003，失敗行為 SuspectedEventsFound = 3。", f"兩台的 3 筆 suspected events 都是 rdsysinfo Event 7000（Slot2 {'、'.join(f2['t7000_post'])}；Slot46 {'、'.join(f46['t7000_post'])}）。",
                   "兩台的 SDK Version 都是 8.2.3.197。"],
         "infer": [], "unknown": ["憑證到期日與簽署者：log 沒有記錄。"], "ev": fail_ev},
        {"sev": "warn", "conf": "已確認", "title": "兩台唯一的事件差異：Slot46 多一筆記憶體型態 CPER",
         "facts": [f"Slot2 的 {f2['cper_n']} 筆 CPER 全是加速器型態；Slot46 的 {f46['cper_n']} 筆中有 {f46['mem']} 筆是 ACPI_ERROR_TYPE_PLATFORM_MEMORY（04:16:31，Pretest）。",
                   "其餘比較項目（CPER 加速器筆數、I2C 訊息、BladeSku、CSI_DER、SEL、PCIe）兩台的數值見下方對照表。",
                   f"兩台都出現：加速器 CPER 各 {f2['acc']} 筆（Slot2）/ {f46['acc']} 筆（Slot46）、I2C bus7 suppress 訊息、CSI_DER 7 筆 eDrive 錯誤。"],
         "infer": [], "unknown": ["這筆記憶體錯誤的影響與重複性：只有一筆，log 沒有更多資訊。詳細原始資料在 Slot46 分頁。"], "ev": []},
    ],
}

data = {"slots": {"s2": {k: v for k, v in s2.items() if k != "_facts"}, "s46": {k: v for k, v in s46.items() if k != "_facts"}}, "compare": compare}
tpl = open(os.path.join(here, "template.html"), encoding="utf-8").read()
app = open(os.path.join(here, "app.js"), encoding="utf-8").read().replace("__DATA__", json.dumps(data, ensure_ascii=False, separators=(",", ":")))
html = tpl.replace("__APP__", app)
open(out, "w", encoding="utf-8").write(html)

# evidence folder
idx = E.copy_evidence(evdir)
for name, text in EXTRA.items():
    open(os.path.join(evdir, name), "w", encoding="utf-8").write(text)
    idx.append(f"(摘錄) {name}")
open(os.path.join(evdir, "INDEX.txt"), "w", encoding="utf-8").write("dashboard 引用的原始檔（與 zip 內路徑相同）\n\n" + "\n".join(idx) + "\n")
print("wrote", out, len(html), "bytes;", len(idx), "evidence entries")
for s, f in (("s2", f2), ("s46", f46)):
    print(s, {k: v for k, v in f.items() if k not in ("sm", "sx", "rx")})
