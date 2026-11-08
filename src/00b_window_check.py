import importlib.util
spec = importlib.util.spec_from_file_location("c", "src/00b_counts.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
kp = m.load_kp().set_index("t").kp
d = kp.rolling("30D").max().resample("D").last()["2015":"2026-09-30"]
print((d >= 6).groupby(d.index.year).mean().round(2))
