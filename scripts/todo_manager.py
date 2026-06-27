import argparse
from pathlib import Path


def add_todo(service, task):
    service_path = Path("services") / service
    if not service_path.exists():
        print(f"Error: Service {service} not found.")
        return
    
    todo_file = service_path / "TODO.md"
    with open(todo_file, "a") as f:
        f.write(f"- [ ] (PENDING) {task}\n")
    print(f"Added to {todo_file}")

def update_todo(service, task_substring, new_status):
    todo_file = Path("services") / service / "TODO.md"
    if not todo_file.exists():
        print(f"Error: {todo_file} not found.")
        return

    lines = todo_file.read_text().splitlines()
    new_lines = []
    found = False
    for line in lines:
        if task_substring in line:
            # Update status flag and mark as checked
            line = line.replace("[ ]", "[x]")
            # Remove old status if present, insert new one
            if "(IN-PROGRESS)" in line:
                line = line.replace("(IN-PROGRESS)", f"({new_status})")
            elif "(PENDING)" in line:
                line = line.replace("(PENDING)", f"({new_status})")
            else:
                line = line.replace("- [x]", f"- [x] ({new_status})")
            found = True
        new_lines.append(line)
    
    if found:
        todo_file.write_text("\n".join(new_lines) + "\n")
        print(f"Updated task in {service}")
    else:
        print("Task not found.")

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
    parser.add_argument("--update", nargs=3, metavar=('SERVICE', 'TASK_SUBSTRING', 'STATUS'))
    parser.add_argument("--sync", action="store_true")
    args = parser.parse_args()

    if args.add:
        add_todo(args.add[0], args.add[1])
    elif args.update:
        update_todo(args.update[0], args.update[1], args.update[2])
    elif args.sync:
        sync_all()