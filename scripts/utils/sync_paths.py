import os

replacements = [
    ("results/evaluation/", "results/evaluation/"),
    ("results/evaluation", "results/evaluation"),
    ("data/eval/", "data/eval/"),
    ("results/hardware/swap_", "results/hardware/swap_"),
    ("results/hardware/bandwidth_", "results/hardware/bandwidth_"),
    ("results/tuning/step1_tuning", "results/tuning/step1_tuning"),
    ("results/tuning/pareto_selection", "results/tuning/pareto_selection"),
    ("results/tuning/sweep_", "results/tuning/sweep_"),
    ("results/tuning/cliff_sensitivity", "results/tuning/cliff_sensitivity"),
    ("models/vector_indices/turbo_index", "models/vector_indices/turbo_index"),
    ("models/vector_indices/outlier_indices", "models/vector_indices/outlier_indices")
]

target_dirs = ["journal_paper_ccpe", "scripts", "src", "README.md", "config.yaml"]

def fix_file(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        original = content
        for old, new in replacements:
            content = content.replace(old, new)
        
        if content != original:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ Fixed: {filepath}")
    except Exception as e:
        print(f"❌ Failed: {filepath} ({e})")

for target in target_dirs:
    if os.path.isfile(target):
        fix_file(target)
    elif os.path.isdir(target):
        for root, dirs, files in os.walk(target):
            for file in files:
                if file.endswith(('.py', '.sh', '.md', '.yaml', '.tex')):
                    fix_file(os.path.join(root, file))

print("Final path synchronization complete.")
