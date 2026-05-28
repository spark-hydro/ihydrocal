from pathlib import Path

from ihydrocal.core.config import print_config_summary
from ihydrocal.core.workspace import setup_workspace


def main():
    script_dir = Path(__file__).resolve().parent
    config_file = script_dir / "../../config/setup_swatplus.yml"

    cfg, workspace_dir, model_dir = setup_workspace(config_file)

    print_config_summary(cfg)
    print(f"Workspace ready: {workspace_dir}")
    print(f"Model ready: {model_dir}")

if __name__ == "__main__":
    main()
