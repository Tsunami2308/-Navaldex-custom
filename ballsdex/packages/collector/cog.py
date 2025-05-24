from ballsdex.core.utils.transformers import BallTransform
import discord
import random
from discord import app_commands
from discord.ext import commands
from datetime import datetime

from ballsdex.core.models import BallInstance, Player, balls, specials
from ballsdex.settings import settings
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ballsdex.core.bot import BallsDexBot

# Define rarity range-based goals
RARITY_COLLECTION_GOALS = [
    ((0.0000000000001, 0.01), 3),
    ((0.01, 0.05), 5),
    ((0.05, 0.1), 8),
    ((0.1, 0.15), 15),
    ((0.15, 0.2), 20),
    ((0.2, 0.3), 35),
    ((0.3, 0.4), 40),
    ((0.4, 0.5), 50),
    ((0.5, 0.6), 55),
    ((0.7, 0.8), 60),
    ((0.8, 0.9), 65),
    ((0.9, float("inf")), 70)
]

# Helper to get collection goal from rarity
def get_collection_goal_by_rarity(rarity: float) -> int:
    for (low, high), goal in RARITY_COLLECTION_GOALS:
        if low <= rarity < high:
            return goal
    return 25  # Fallback if not matched

class Collector(commands.GroupCog, group_name="collector"):
    """
    Collector Code command
    """
    def __init__(self, bot: "BallsDexBot"):
        self.bot = bot

    @app_commands.command()
    async def progress(self, interaction: discord.Interaction, ship: BallTransform):
        """
        Check the player's progress towards collecting enough collectibles to get the Collector card.

        Parameters:
        ship: BallTransform
            The ship you want to see progress for.
        """
        await interaction.response.defer(ephemeral=True, thinking=True)

        player = await Player.get_or_none(discord_id=interaction.user.id)
        if not player:
            await interaction.followup.send("You don't have any ships yet!", ephemeral=True)
            return

        # Fetch user's collectibles (balls)
        user_balls = await BallInstance.filter(player=player).select_related("ball")

        if not user_balls:
            await interaction.followup.send("You have no collectibles yet!", ephemeral=True)
            return

        # Filter balls to check for the specific flock (target collectible)
        target_ball_instances = [ball for ball in user_balls if ball.ball == ship]

        # Count the total number of specific flock balls the player has
        total_target_balls = len(target_ball_instances)

        # Get collection goal based on rarity range
        rarity = ship.rarity
        COLLECTION_GOAL = get_collection_goal_by_rarity(rarity)

        # Calculate remaining
        remaining = max(0, COLLECTION_GOAL - total_target_balls)

        # Send progress information
        embed = discord.Embed(title="Collection Progress", color=discord.Colour.from_rgb(168, 199, 247))
        embed.add_field(name="Total Collectibles", value=f"**{total_target_balls}** {ship.country}", inline=False)
        embed.add_field(name="Collectible Goal", value=f"**{COLLECTION_GOAL}**", inline=False)
        embed.add_field(name="Remaining to Unlock", value=f"**{remaining}**", inline=False)

        await interaction.followup.send(embed=embed, ephemeral=True)    
    @app_commands.command()
    async def claim(self, interaction: discord.Interaction, ship: BallTransform):
        """
        Reward the user with the Collector card if they have collected enough items.

        Parameters:
        ship: BallTransform
            The flock you want to claim.
        """
        await interaction.response.defer(ephemeral=True, thinking=True)

        player = await Player.get_or_none(discord_id=interaction.user.id)
        if not player:
            await interaction.followup.send("You don't have any ships yet!", ephemeral=True)
            return

        user_balls = await BallInstance.filter(player=player).select_related("ball")

        if not user_balls:
            await interaction.followup.send("You have no collectibles yet!", ephemeral=True)
            return

        target_ball_instances = [ball for ball in user_balls if ball.ball_id == ship.pk]
        total_target_balls = len(target_ball_instances)

        rarity = ship.rarity
        COLLECTION_GOAL = get_collection_goal_by_rarity(rarity)

        special = next((x for x in specials.values() if x.name == "Collector"), None)
        if not special:
            await interaction.followup.send("Collector card not found! Please contact support.", ephemeral=True)
            return

        has_special_card = any(
            ball.special_id == special.pk and ball.ball.country == ship.country 
            for ball in user_balls
        )

        if has_special_card:
            reward_text = "You already have the Collector card for this ship!"
        else:
            if total_target_balls >= COLLECTION_GOAL:
                special_ball = next(
                    (ball for ball in balls.values() if ball.country == ship.country), 
                    None
                )
                if not special_ball:
                    await interaction.followup.send("Special ball not found! Please contact support.", ephemeral=True)
                    return

                await BallInstance.create(
                    ball=special_ball,
                    player=player,
                    server_id=interaction.guild_id,
                    attack_bonus=random.randint(-20, 20),
                    health_bonus=random.randint(-20, 20),
                    special=special
                )
                reward_text = "The Collector card has been added to your collection!"
            else:
                reward_text = f"You have **{total_target_balls}/{COLLECTION_GOAL}** {ship.country}'s. Keep grinding to unlock the Collector card!"

        embed = discord.Embed(title="Collector Card Reward", color=discord.Colour.from_rgb(168, 199, 247))
        embed.add_field(name="Total Collectibles", value=f"**{total_target_balls}** {ship.country}", inline=False)
        embed.add_field(name="Special Reward", value=reward_text, inline=False)
