import asyncio
import uuid

from app.core.security import hash_password
from app.db.session import get_session_maker
from app.models.base import \
    Base  # or app.db.base depending on your naming convention
from app.models.role import Role
from app.models.user import User
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

# Setup static definitions matching your application constraints
DEFAULT_ROLES = [
    {"name": "admin", "description": "Superuser with unrestricted platform authorization privileges."},
    {"name": "manager", "description": "Internal operations manager with administrative oversight."},
    {"name": "user", "description": "Standard base operational platform account registration level."}
]

SEED_USER = {
    "email": "admin@example.com",
    "password": "SuperSecurePassword123!",  # Change this immediately for production environments
    "is_superuser": True,
    "is_verified": True,
    "is_active": True,
    "role_name": "admin"
}


async def seed_system_data(session: AsyncSession) -> None:
    """
    Idempotent seeding operation executing roles initialization 
    and primary superuser credential provisioning.
    """
    print("[*] Beginning IAM Database Seeding Sequence...")

    # 1. Seed RBAC Roles
    role_map: dict[str, Role] = {}
    for role_data in DEFAULT_ROLES:
        query = select(Role).where(Role.name == role_data["name"])
        result = await session.execute(query)
        existing_role = result.scalar_one_or_none()

        if not existing_role:
            print(f"[+] Role '{role_data['name']}' not found. Seeding component...")
            new_role = Role(
                name=role_data["name"],
                description=role_data["description"]
            )
            session.add(new_role)
            role_map[role_data["name"]] = new_role
        else:
            print(f"[-] Role '{role_data['name']}' already exists. Skipping.")
            role_map[role_data["name"]] = existing_role

    # Flush changes to ensure roles have transient/persistent relationships ready
    await session.flush()

    # 2. Seed Master Administrative User Account Entity
    user_query = select(User).where(User.email == SEED_USER["email"])
    user_result = await session.execute(user_query)
    existing_user = user_result.scalar_one_or_none()

    if not existing_user:
        print(f"[+] Core account '{SEED_USER['email']}' not found. Provisioning system master matrix...")
        
        hashed = hash_password(SEED_USER["password"])
        admin_role = role_map[SEED_USER["role_name"]]

        super_user = User(
            email=SEED_USER["email"],
            password_hash=hashed,
            is_active=SEED_USER["is_active"],
            is_verified=SEED_USER["is_verified"],
            is_superuser=SEED_USER["is_superuser"],
            roles=[admin_role]  # Link directly to the relational database object mapping
        )
        session.add(super_user)
        print(f"[!] Superuser successfully initialized with email: {SEED_USER['email']}")
    else:
        print(f"[-] Account profile '{SEED_USER['email']}' already present. Skipping profile seeding.")

    # Commit the transaction matrix atomically
    await session.commit()
    print("[*] Database Seeding Complete.")


async def main() -> None:
    session_maker = get_session_maker()
    
    async with session_maker() as session:
        try:
            await seed_system_data(session)
        except Exception as e:
            await session.rollback()
            print(f"[CRITICAL] Transaction rolled back due to error processing seeding parameters: {e}")
            raise e


if __name__ == "__main__":
    # Initialize the asynchronous execution framework loop
    asyncio.run(main())