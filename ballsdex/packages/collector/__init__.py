from typing import TYPE_CHECKING

from ballsdex.packages.collector.cog import Collector

if TYPE_CHECKING:
    from ballsdex.core.bot import BallsDexBot

async def setup(bot: "BallsDexBot"):
    await bot.add_cog(Collector(bot))
