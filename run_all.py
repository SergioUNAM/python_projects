from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parent


def main() -> None:
    demos = ["range_audit", "provider_reconciliation", "portout_retention"]
    for demo in demos:
        print(f"\n=== {demo} ===")
        subprocess.run([sys.executable, str(ROOT / demo / "run.py")], check=True)


if __name__ == "__main__":
    main()

