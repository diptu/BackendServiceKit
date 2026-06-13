import asyncio

from app.core.security import hash_password
from app.db.session import get_session_maker
from app.models.role import Role
from app.models.user import User
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

# 5 Dummy Users Matrix spanning different authorization scopes
TEST_USERS = [
    {
        "email": "test_admin@example.com",
        "password": "PasswordAdmin123!",
        "is_superuser": True,
        "is_verified": True,
        "role_name": "admin"
    },
    {
        "email": "test_manager1@example.com",
        "password": "PasswordManager123!",
        "is_superuser": False,
        "is_verified": True,
        "role_name": "manager"
    },
    {
        "email": "test_user1@example.com",
        "password": "PasswordUser123!",
        "is_superuser": False,
        "is_verified": True,
        "role_name": "user"
    },
    {
        "email": "test_user2@example.com",
        "password": "PasswordUser123!",
        "is_superuser": False,
        "is_verified": True,
        "role_name": "user"
    },
    {
        "email": "unverified_user@example.com",
        "password": "PasswordUser123!",
        "is_superuser": False,
        "is_verified": False,  # Useful for testing verification block restrictions
        "role_name": "user"
    }
]

async def seed_test_data(session: AsyncSession) -> None:
    print("[*] Resolving platform roles from database...")
    
    # Pre-fetch existing roles to establish relations
    roles_result = await session.execute(select(Role))
    roles_list = roles_result.scalars().all()
    role_map = {role.name: role for role in roles_list}
    
    # Basic structural check to verify roles are seeded
    if not role_map:
        print("[ERROR] Base system roles not found. Run your main seed.py file first.")
        return

    print("[*] Injecting 5 dummy test user profiles into database configuration...")
    
    for user_data in TEST_USERS:
        # Prevent unique constraint crashes on repetitive execution runs
        user_query = select(User).where(User.email == user_data["email"])
        user_result = await session.execute(user_query)
        existing_user = user_result.scalar_one_or_none()
        
        if not existing_user:
            target_role = role_map.get(user_data["role_name"])
            if not target_role:
                print(f"[-] Role '{user_data['role_name']}' missing. Skipping {user_data['email']}.")
                continue
                
            hashed = hash_password(user_data["password"])
            
            new_test_user = User(
                email=user_data["email"],
                password_hash=hashed,
                is_active=True,
                is_verified=user_data["is_verified"],
                is_superuser=user_data["is_superuser"],
                roles=[target_role]
            )
            session.add(new_test_user)
            print(f"[+] Provisioned: {user_data['email']} [{user_data['role_name']}]")
        else:
            print(f"[-] User '{user_data['email']}' already exists. Skipping.")

    await session.commit()
    print("[*] Test environment population complete.")

async def main() -> None:
    session_maker = get_session_maker()
    async with session_maker() as session:
        try:
            await seed_test_data(session)
        except Exception as e:
            await session.rollback()
            print(f"[CRITICAL] Seeding failed. Transactions rolled back: {e}")
            raise e

if __name__ == "__main__":
    asyncio.run(main())