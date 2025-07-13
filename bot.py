import discord
from discord.ext import commands
import io
import os
from dotenv import load_dotenv

# Import the image processing functions from our local file
from biggify_image import biggify_image, merge_images 

# Load environment variables from the .env file
load_dotenv()
TOKEN = os.getenv('DISCORD_BOT_TOKEN')

# Define Discord Intents
intents = discord.Intents.default()
intents.message_content = True 
intents.messages = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    """
    Event that fires when the bot successfully connects to Discord.
    Used to sync slash commands.
    """
    print(f'Logged in as {bot.user.name} ({bot.user.id})')
    print('------')
    try:
        # Sync slash commands globally
        await bot.tree.sync() 
        print("Slash commands synced successfully.")
    except Exception as e:
        print(f"Error syncing slash commands: {e}")

@bot.tree.command(name="biggify", description="Stretches an attached image horizontally and splits it into strips.")
@discord.app_commands.describe(
    image="The image to biggify (attach it to the command).",
    rows="Number of horizontal strips to split the image into (default: 4, max 10).",
    stretch_factor="How much to stretch the image horizontally (1.0-3.0, default: 1.5). Larger is more stretch."
)
async def biggify(interaction: discord.Interaction, image: discord.Attachment, rows: int = 4, stretch_factor: float = 1.5):
    """
    Handles the /biggify slash command.
    Takes an attached image, stretches it horizontally, and then splits that
    stretched image into horizontal strips, sending each as a separate message
    without the "Click to see command" annotation, and appearing grouped.
    The output strips are scaled up by a default factor of 2.0.
    """
    # Defer the response ephemerally. This acknowledges the command to the user
    # but doesn't show a public "thinking" message or the "Click to see command" annotation.
    await interaction.response.defer(thinking=True, ephemeral=True) 

    # 1. Input Validation
    if not image or not image.content_type.startswith('image/'):
        # Send an ephemeral error message if validation fails
        await interaction.followup.send("Please attach a valid image to the command!", ephemeral=True)
        return
    
    if not (1 <= rows <= 10): 
        await interaction.followup.send("Rows must be between 1 and 10 (inclusive).", ephemeral=True)
        return
    
    if not (1.0 <= stretch_factor <= 3.0):
        await interaction.followup.send("Stretch factor must be between 1.0 and 3.0 (e.g., 1.5). Larger values mean more stretch.", ephemeral=True)
        return

    # Set the default output_scale_factor here
    default_output_scale_factor = 2.0 # You can adjust this value (e.g., 1.5, 2.5, 3.0)

    # 2. Download the image from the attachment
    try:
        image_bytes = await image.read()
    except discord.errors.HTTPException as e:
        print(f"HTTP Error downloading image: {e}")
        await interaction.followup.send(f"Could not download the image. Please try again. Error: {e}", ephemeral=True)
        return
    except Exception as e:
        print(f"Unexpected error downloading image: {e}")
        await interaction.followup.send(f"An unexpected error occurred while downloading the image. Error: {e}", ephemeral=True)
        return

    # 3. Process the image using our biggify_image function
    # Pass the default_output_scale_factor
    processed_images = biggify_image(image_bytes, rows, stretch_factor, default_output_scale_factor)

    if not processed_images:
        await interaction.followup.send("An error occurred while processing the image. Please try again with a different image or settings.", ephemeral=True)
        return

    # 4. Send the "biggified" images back to Discord, each in a separate message, directly to the channel.
    for i, img_data in enumerate(processed_images):
        try:
            file_name = f"biggified_part_{i+1}.png"
            # Send directly to the channel
            await interaction.channel.send(file=discord.File(fp=img_data, filename=file_name))
        except Exception as e:
            print(f"Error sending individual file {i+1}: {e}")
            await interaction.followup.send(f"Could not send part {i+1} due to an error.", ephemeral=True)
            pass 

    # Optionally, send a final ephemeral message to confirm completion
    await interaction.followup.send("Image biggified and sent!", ephemeral=True)


@bot.tree.command(name="mergebiggify", description="Merges multiple biggified image strips into a single image.")
@discord.app_commands.describe(
    image1="The first image strip (required).",
    image2="The second image strip (optional).",
    image3="The third image strip (optional).",
    image4="The fourth image strip (optional).",
    image5="The fifth image strip (optional).",
    image6="The sixth image strip (optional).",
    image7="The seventh image strip (optional).",
    image8="The eighth image strip (optional).",
    image9="The ninth image strip (optional).",
    image10="The tenth image strip (optional)."
)
async def mergebiggify(
    interaction: discord.Interaction,
    image1: discord.Attachment,
    image2: discord.Attachment = None,
    image3: discord.Attachment = None,
    image4: discord.Attachment = None,
    image5: discord.Attachment = None,
    image6: discord.Attachment = None,
    image7: discord.Attachment = None,
    image8: discord.Attachment = None,
    image9: discord.Attachment = None,
    image10: discord.Attachment = None,
):
    """
    Handles the /mergebiggify slash command.
    Takes up to 10 attached image strips and merges them vertically into a single image.
    """
    await interaction.response.defer(thinking=True, ephemeral=True)

    attached_images = [
        image1, image2, image3, image4, image5,
        image6, image7, image8, image9, image10
    ]
    
    # Filter out None values and ensure they are images
    valid_images = [
        img for img in attached_images 
        if img is not None and img.content_type and img.content_type.startswith('image/')
    ]

    if not valid_images:
        await interaction.followup.send("Please attach at least one valid image strip to merge.", ephemeral=True)
        return
    
    if len(valid_images) < 2:
        await interaction.followup.send("Please attach at least two image strips to merge them effectively.", ephemeral=True)
        return

    image_bytes_list = []
    for img_attachment in valid_images:
        try:
            image_bytes_list.append(await img_attachment.read())
        except discord.errors.HTTPException as e:
            print(f"HTTP Error downloading image for merge: {e}")
            await interaction.followup.send(f"Could not download one of the images for merging. Error: {e}", ephemeral=True)
            return
        except Exception as e:
            print(f"Unexpected error downloading image for merge: {e}")
            await interaction.followup.send(f"An unexpected error occurred while downloading images for merging. Error: {e}", ephemeral=True)
            return

    # Call the merge_images function
    merged_image_io = merge_images(image_bytes_list)

    if merged_image_io:
        try:
            # Send the merged image directly to the channel
            await interaction.channel.send(file=discord.File(fp=merged_image_io, filename="merged_biggified_image.png"))
            await interaction.followup.send("Images merged successfully!", ephemeral=True)
        except discord.errors.HTTPException as e:
            print(f"Error sending merged image: {e}")
            await interaction.followup.send(f"Could not send the merged image (likely too large). Error: {e}", ephemeral=True)
        except Exception as e:
            print(f"An unexpected error occurred while sending the merged image: {e}")
            await interaction.followup.send(f"An unexpected error occurred while sending the merged image: {e}", ephemeral=True)
    else:
        await interaction.followup.send("An error occurred while merging the images. Please ensure they are valid image strips.", ephemeral=True)


# Run the bot
if TOKEN:
    bot.run(TOKEN)
else:
    print("Error: DISCORD_BOT_TOKEN not found in your .env file.")
    print("Please create a .env file in the same directory as bot.py and add: DISCORD_BOT_TOKEN=YOUR_BOT_TOKEN_HERE")
    print("You can get your bot token from the Discord Developer Portal (Bot section).")
