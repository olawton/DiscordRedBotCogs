from redbot.core import commands, Config
import asyncio
import parsedatetime
import datetime
import discord
import pytz
import re

class TimeReply(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.pdt_calendar = parsedatetime.Calendar()
        self.config = Config.get_conf(self, identifier=1234567890)
        self.config.register_user(timezone=None)

    @commands.command()
    async def timezoneset(self, ctx, timezone: str = None):
        """Set preferred timezone using a valid pytz timezone string."""
        if timezone is None:
            await ctx.send("Please provide a location timezone (e.g., `America/New_York`). List of valid timezones: https://pastebin.com/raw/1jtNpJiU")
            return

        if timezone not in pytz.all_timezones:
            await ctx.send("That timezone is not valid. Please use a recognized location timezone from pytz. List of valid timezones: https://pastebin.com/raw/1jtNpJiU")
            return

        await self.config.user(ctx.author).timezone.set(timezone)
        await ctx.send(f"Your timezone has been set to `{timezone}`!")

    @commands.command()
    async def timezone(self, ctx):
        """Display currently saved timezone."""
        tz = await self.config.user(ctx.author).timezone()
        if tz:
            await ctx.send(f"Your current timezone is: `{tz}`")
        else:
            await ctx.send("You haven't set a timezone yet. Use `!timezoneset <timezone>` to set one.")

    @commands.command()
    async def timezoneclear(self, ctx):
        """Clear saved timezone."""
        await self.config.user(ctx.author).timezone.set(None)
        await ctx.send("Your timezone has been cleared.")

    @commands.command()
    async def timezonetestbad(self, ctx):
        """Set an invalid string to simulate broken timezone behavior."""
        await self.config.user(ctx.author).timezone.set("banana/timehole")
        await ctx.send("Your timezone has been set to an invalid string for testing.")

    @commands.Cog.listener()
    async def on_message(self, message):
        # Ignore messages from bots.
        if message.author.bot:
            return

        content = message.content
        
        # Check if message contains an explicit time in multiple formats ("9pm", "921pm" "9:21 PM" "9 p.m." etc.)
        pattern = r'\b\d{1,4}(?::\d{2})?\s*(a\.?m\.?|p\.?m\.?)\b'
        if not re.search(pattern, content.lower()):
            return

        parsed_dt, status = self.pdt_calendar.parseDT(content, sourceTime=datetime.datetime.now())
        if status == 0:
            return
        
        emoji_clock = "🕒"
        emoji_page = "📄"
        await message.add_reaction(emoji_clock)
        await message.add_reaction(emoji_page)


        responded = set()

        while True:
            try:
                # Listens for reactions for 600 seconds
                reaction, user = await self.bot.wait_for("reaction_add", timeout=600.0, check=lambda r, u: r.message.id == message.id and str(r.emoji) in [emoji_clock, emoji_page] and not u.bot)

                # If sender did not have their timezone set:
                sender_tz = await self.config.user(message.author).timezone()
                if not sender_tz:
                    await message.reply(f"{message.author.mention} needs to set their timezone using `!timezoneset <timezone>`. List of valid timezones: https://pastebin.com/raw/1jtNpJiU")
                    break
                
                tz = pytz.timezone(sender_tz)
                if parsed_dt.tzinfo is None:
                    localized_dt = tz.localize(parsed_dt)
                else:
                    localized_dt = parsed_dt.astimezone(tz)

                unix = int(localized_dt.timestamp())

                # Short option represented by clock emoji embeds full timestamp and relative timestamp.
                if str(reaction.emoji) == emoji_clock and "clock" not in responded:
                    formatted = f"<t:{unix}:F> (<t:{unix}:R>)"
                    await message.reply(formatted, allowed_mentions=discord.AllowedMentions(replied_user=False))
                    responded.add("clock")

                # Longer option represented by page emoji shows all timestamp formats for easy copy/paste elsewhere.
                elif str(reaction.emoji) == emoji_page and "page" not in responded:
                    embed = discord.Embed(
                        title=f"Timestamps for <t:{unix}:F>",
                        color=discord.Color.red(),
                        description=(
                            f"`<t:{unix}:F>`: <t:{unix}:F>\n"
                            f"`<t:{unix}:f>`: <t:{unix}:f>\n"
                            f"`<t:{unix}:D>`: <t:{unix}:D>\n"
                            f"`<t:{unix}:d>`: <t:{unix}:d>\n"
                            f"`<t:{unix}:T>`: <t:{unix}:T>\n"
                            f"`<t:{unix}:t>`: <t:{unix}:t>\n"
                            f"`<t:{unix}:R>`: <t:{unix}:R>"
                        )
                    )
                    await message.reply(embed=embed, allowed_mentions=discord.AllowedMentions(replied_user=False))
                    responded.add("page")
            except asyncio.TimeoutError:
                break
            except Exception as err:
                await message.reply(f"ERROR: {err}")
                return

def setup(bot):
    bot.add_cog(TimeReply(bot))
