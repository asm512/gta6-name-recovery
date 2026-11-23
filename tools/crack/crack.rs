// probability ranked name cracker
// names are sequences of tokens: a first token, middle tokens and a last token, each drawn from a list ranked by how
// often it holds that position in known names. every sequence whose rank product is under a bound is hashed and tested
// against the wanted hashes and against random decoys, so the chance match rate can be read off for any score cut.
// usage: crack <in dir> <class> <threads> <bound for 2 tokens> <bound for 3> ... (one bound per length, 0 skips)
use std::collections::HashSet;
use std::io::Write;
use std::sync::atomic::{AtomicUsize, Ordering};
use std::sync::Mutex;

#[inline]
fn feed(mut h: u32, bytes: &[u8]) -> u32 {
    for &b in bytes {
        h = h.wrapping_add(b as u32);
        h = h.wrapping_add(h << 10);
        h ^= h >> 6;
    }
    h
}

#[inline]
fn finish(mut h: u32) -> u32 {
    h = h.wrapping_add(h << 3);
    h ^= h >> 11;
    h.wrapping_add(h << 15)
}

fn lines(path: &str, cap: usize) -> Vec<String> {
    std::fs::read_to_string(path).unwrap_or_default().lines().filter(|l| !l.is_empty()).take(cap).map(str::to_string).collect()
}

struct Ctx<'a> {
    mid: &'a [String],
    last: &'a [String],
    bits: &'a [u64],
    wanted: &'a HashSet<u32>,
    decoys: &'a HashSet<u32>,
    bound: u64,
}

struct Out {
    hits: Vec<(u64, u32, String)>,
    decoy_scores: Vec<u64>,
    tried: u64,
}

fn rec(ctx: &Ctx, state: u32, prod: u64, mids_left: usize, stack: &mut Vec<u32>, first: &str, out: &mut Out) {
    if mids_left == 0 {
        let limit = (ctx.bound / prod).min(ctx.last.len() as u64) as usize;
        out.tried += limit as u64;
        for (z, tok) in ctx.last[..limit].iter().enumerate() {
            let h = finish(feed(state, tok.as_bytes()));
            if ctx.bits[(h >> 12) as usize] & (1 << ((h >> 6) & 63)) == 0 {
                continue;
            }
            let score = prod * (z as u64 + 1);
            if ctx.wanted.contains(&h) {
                let mut name = first.to_string();
                for &m in stack.iter() {
                    name.push_str(&ctx.mid[m as usize]);
                }
                name.push_str(tok);
                out.hits.push((score, h, name));
            } else if ctx.decoys.contains(&h) {
                out.decoy_scores.push(score);
            }
        }
        return;
    }
    let limit = (ctx.bound / prod).min(ctx.mid.len() as u64) as usize;
    for (k, tok) in ctx.mid[..limit].iter().enumerate() {
        stack.push(k as u32);
        rec(ctx, feed(state, tok.as_bytes()), prod * (k as u64 + 1), mids_left - 1, stack, first, out);
        stack.pop();
    }
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    let dir = &args[1];
    let class = &args[2];
    let threads: usize = args[3].parse().unwrap();
    let bounds: Vec<u64> = args[4..].iter().map(|a| a.parse::<f64>().unwrap() as u64).collect();
    let first = lines(&format!("{dir}/first_{class}.txt"), 20000);
    let mid = lines(&format!("{dir}/mid_{class}.txt"), 20000);
    let last = lines(&format!("{dir}/last_{class}.txt"), 20000);
    let wanted: HashSet<u32> = lines(&format!("{dir}/targets_{class}.txt"), usize::MAX).iter().filter_map(|l| u32::from_str_radix(l, 16).ok()).collect();
    let all: HashSet<u32> = lines(&format!("{dir}/all_targets.txt"), usize::MAX).iter().filter_map(|l| u32::from_str_radix(l, 16).ok()).collect();
    let mut decoys = HashSet::new();
    let mut x = 0x2545_f491_4f6c_dd1du64 ^ wanted.len() as u64;
    while decoys.len() < wanted.len() * 4 {
        x ^= x << 13;
        x ^= x >> 7;
        x ^= x << 17;
        let h = (x >> 16) as u32;
        if !all.contains(&h) {
            decoys.insert(h);
        }
    }
    let mut bits = vec![0u64; 1 << 20];
    for h in wanted.iter().chain(&decoys) {
        bits[(h >> 12) as usize] |= 1 << ((h >> 6) & 63);
    }
    eprintln!("{class}: {} wanted, {} first, {} mid, {} last tokens", wanted.len(), first.len(), mid.len(), last.len());
    let stdout = Mutex::new(std::io::BufWriter::new(std::io::stdout()));
    for (i, &bound) in bounds.iter().enumerate() {
        let len = i + 2;
        if bound == 0 {
            continue;
        }
        let ctx = Ctx { mid: &mid, last: &last, bits: &bits, wanted: &wanted, decoys: &decoys, bound };
        let next = AtomicUsize::new(0);
        let total = AtomicUsize::new(0);
        let started = std::time::Instant::now();
        let top = (bound.min(first.len() as u64)) as usize;
        std::thread::scope(|s| {
            for _ in 0..threads {
                s.spawn(|| {
                    let mut out = Out { hits: Vec::new(), decoy_scores: Vec::new(), tried: 0 };
                    let mut stack = Vec::new();
                    loop {
                        let a = next.fetch_add(1, Ordering::Relaxed);
                        if a >= top {
                            break;
                        }
                        rec(&ctx, feed(0, first[a].as_bytes()), a as u64 + 1, len - 2, &mut stack, &first[a], &mut out);
                    }
                    total.fetch_add(out.tried as usize, Ordering::Relaxed);
                    let mut w = stdout.lock().unwrap();
                    for (score, h, name) in out.hits {
                        let _ = writeln!(w, "H\t{len}\t{score}\t{h:08x}\t{name}");
                    }
                    for score in out.decoy_scores {
                        let _ = writeln!(w, "D\t{len}\t{score}");
                    }
                });
            }
        });
        eprintln!("  {class} len {len} bound {bound:e}: {:.3e} candidates in {:.1}s", total.load(Ordering::Relaxed) as f64, started.elapsed().as_secs_f32());
    }
    // single tokens from the first list
    let mut w = stdout.lock().unwrap();
    for (a, tok) in first.iter().enumerate() {
        let h = finish(feed(0, tok.as_bytes()));
        if wanted.contains(&h) {
            let _ = writeln!(w, "H\t1\t{}\t{h:08x}\t{tok}", a + 1);
        } else if decoys.contains(&h) {
            let _ = writeln!(w, "D\t1\t{}", a + 1);
        }
    }
}
