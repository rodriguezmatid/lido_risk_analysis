from scipy.stats import binom

n = 259019
p = 49/259019
k = int(0.1 * 259019)

probabilidad = binom.pmf(k, n, p)
print(f"{probabilidad:.90f}")