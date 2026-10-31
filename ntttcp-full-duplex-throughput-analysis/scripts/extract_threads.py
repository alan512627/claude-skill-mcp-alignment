"""Per-thread throughput (Mbps) from an NTTTCP sender.xml / receiver.xml -> CSV 'index,Mbps'.
usage: python -I extract_threads.py <xml> <out.csv>"""
import re, sys
text = open(sys.argv[1], encoding="utf-8-sig").read()
rows = re.findall(r'<thread index="(\d+)">.*?<throughput metric="mbps">([-\d.]+)</throughput>.*?</thread>', text, re.S)
open(sys.argv[2], "w", encoding="utf-8").write("\n".join(f"{i},{v}" for i, v in rows) + "\n")
print(len(rows), "threads")
