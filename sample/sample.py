import asyncio
import logging
import sys

from aiokem.main import AioKem

# Configure the logger
_LOGGER = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


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
            _LOGGER.info("Utility Voltage: %s", data["utilityVoltageV"])
        await asyncio.sleep(60)  # Sleep for 1 minute before fetching again


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python sample.py <username> <password>")
        sys.exit(1)

    username = sys.argv[1]
    password = sys.argv[2]
    asyncio.run(main(username, password))
