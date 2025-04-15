import asyncio
import sys
from datetime import datetime

from aiokem.main import AioKem


async def main(username: str, password: str) -> None:
    """Main function to demonstrate the usage of AioKem."""
    # Create an instance of AioKem
    # You can pass a custom session if needed, otherwise it will create a new one
    kem = AioKem()

    # Call the login method
    await kem.authenticate(username, password)

    # Get the list of homes
    homes = await kem.get_homes()

    # For each home, get the generator data
    while True:
        for home in homes:
            data = await kem.get_generator_data(int(home["id"]))
            print(
                f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - "
                f"Utility Voltage: {data['utilityVoltageV']}"
            )
        await asyncio.sleep(60)  # Sleep for 1 minute before fetching again


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python sample.py <username> <password>")
        sys.exit(1)

    username = sys.argv[1]
    password = sys.argv[2]
    asyncio.run(main(username, password))
