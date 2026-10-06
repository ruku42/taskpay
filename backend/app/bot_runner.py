from app.bot import create_bot
import asyncio

async def main():
    bot = create_bot()
    await bot.initialize()
    await bot.start()
    await bot.updater.start_polling()

    try:
        await asyncio.Event().wait()
    finally:
        await bot.updater.stop()
        await bot.stop()
        await bot.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
