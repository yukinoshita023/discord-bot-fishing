import discord

async def setup(bot):

    @bot.tree.command(name="hello", description="このコマンドによってメイシシステムの生存確認ができます")
    async def hello(interaction: discord.Interaction):
        await interaction.response.send_message("職務遂行中です！")