import asyncio
import logging
import sys

from aiohttp import ClientSession

from aiokem.main import AioKem

# Configure the logger
_LOGGER = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


async def on_refresh_token_update(refresh_token: str | None) -> None:
    """Handle the refresh token update."""
    _LOGGER.info("Refresh token updated: %s", refresh_token)


async def main(email: str, password: str) -> None:
    """Main function to demonstrate the usage of AioKem."""
    # Create an instance of AioKem
    async with ClientSession() as session:
        kem = AioKem(session=session)
        # Retry 2x with 1 and 2 seconds delays
        kem.set_retry_policy(retry_count=2, retry_delays=[1, 2])
        kem.set_refresh_token_callback(on_refresh_token_update)

        # Call the login method
        await kem.authenticate(email, password)

        # Get the list of homes
        homes = await kem.get_homes()

        # For each home, get the generator data
        try:
            while True:
                for home in homes:
                    generator_id = int(home["id"])
                    data = await kem.get_generator_data(generator_id)
                    _LOGGER.info("Utility Voltage: %s", data["utilityVoltageV"])

                    # Check for alerts.
                    if data["device"]["alertCount"]:
                        alerts = await kem.get_alerts(generator_id)
                        for alert in alerts:
                            _LOGGER.info(f"Alert ({alert['type']}): {alert['name']}")

                await asyncio.sleep(60)  # Sleep for 1 minute before fetching again
        except KeyboardInterrupt:
            _LOGGER.info("Exiting...")
        except Exception as e:
            _LOGGER.error("An error occurred: %s", e)
        await kem.close()


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python sample.py <email> <password>")
        sys.exit(1)

    email = sys.argv[1]
    password = sys.argv[2]
    asyncio.run(main(email, password))
