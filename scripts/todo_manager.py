import argparse
from pathlib import Path


def add_todo(service, task):
    service_path = Path("services") / service
    if not service_path.exists():
        print(f"Error: Service {service} not found.")
        return
    
    todo_file = service_path / "TODO.md"
    with open(todo_file, "a") as f:
        f.write(f"- [ ] {task}\n")
    print(f"Added to {todo_file}")

def sync_all():
    root_todo = Path("TODO.md")
    content = "# Project Master Task Board\n\n"
    
    for service_dir in sorted(Path("services").iterdir()):
        if service_dir.is_dir():
            todo_file = service_dir / "TODO.md"
            if todo_file.exists():
                content += f"## {service_dir.name}\n"
                content += todo_file.read_text() + "\n\n"
    
    root_todo.write_text(content)
    print("Master TODO.md synchronized.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--add", nargs=2, metavar=('SERVICE', 'TASK'))
    parser.add_argument("--sync", action="store_true")
    args = parser.parse_args()

    if args.add:
        add_todo(args.add[0], args.add[1])
    elif args.sync:
        sync_all()