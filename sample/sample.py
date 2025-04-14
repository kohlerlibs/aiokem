import asyncio
import json

from src.aiokem.main import AioKem

USERNAME = "me"
PASSWORD = "password"  # noqa: S105


async def main():
    """Main function to demonstrate the usage of AioKem."""
    # Create an instance of AioKem
    # You can pass a custom session if needed, otherwise it will create a new one
    kem = AioKem()

    # Call the login method
    await kem.login(USERNAME, PASSWORD)

    # Get the list of homes
    homes = await kem.get_homes()
    print(json.dumps(homes, indent=4))

    # For each home, get the generator data
    for home in homes:
        data = await kem.get_generator_data(home["id"])
        print(json.dumps(data, indent=4))

    await kem.close()


if __name__ == "__main__":
    asyncio.run(main())
