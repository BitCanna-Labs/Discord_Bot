import discord
from discord.ext import commands
import random
from discord.user import BaseUser
import requests
from datetime import datetime
import json

from mytoken import secret
from greetings import greetings

# CREATES A NEW BOT OBJECT WITH A SPECIFIED PREFIX. 
# OLD
# client = commands.Bot(command_prefix =  '!')
# NEW
intents = discord.Intents.default()
intents.message_content = True

client = commands.Bot(command_prefix='!', description='BotCanna here!',intents=intents)

# TELLS WHEN THE BOT IS READY AFTER IT HAS LAUNCHED.
@client.event
async def on_ready():
    print('We have logged in as {0.user}'.format(client))
    print('Bot has initialized and is ready for operation!')
    await client.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name='Bob Marley'))

# SENDS A RANDOM GREETING MESSAGE WHEN A USER TYPES BotCanna
@client.event
async def on_message(message):
    if message.author == client.user:
        return

    msg = message.content
    if 'BotCanna' in msg:
        await message.channel.send(random.choice(greetings))
    await client.process_commands(message)

# GETS THE LATEST COINDEAL INFO FROM THEIR API
@client.command(name='getcoindeal', hidden=True)
async def getcoindeal(ctx):
    '''This will show the current price info on CoinDeal'''
    url = 'https://coinmarketcap.coindeal.com/api/v1/ticker'
    try:
        response = requests.get(url,headers={'Accept': 'application/json'},)
    except:
        pass
    else:
        data = response.json()
        array_prices = data['BCNA_BTC']
        btc_usd_prices = data['BTC_USDT']
        # btc_eur_prices = data['BTC_EUR']
        last_price = float(array_prices['last'])
        volume = float(array_prices['quoteVolume'])
        high_price = float(array_prices['high24hr'])
        high_bid = float(array_prices['highestBid'])
        lowest_ask = float(array_prices['lowestAsk'])
        base_volume = float(array_prices['baseVolume'])
        price_usd = float(float(array_prices['last']) * float(btc_usd_prices['last']))
        # price_eur = float(float(array_prices['last']) * float(btc_eur_prices['last']))
        embed=discord.Embed(title='BCNA / BTC at CoinDeal', url='https://frontend.coindeal.com/market/BCNA-BTC/', color=0x74ECF7)
        embed.set_thumbnail(url='https://static.coindeal.com/landing-page-assets/favicons/apple-icon-120x120.png')
        embed.add_field(name='Price BTC', value=('{:>0.8f}'.format(last_price)+' BTC'), inline=True)
        embed.add_field(name='Price USD', value=('{:>0.4f}'.format(price_usd)+' USD'), inline=True)
        embed.add_field(name='Volume', value=('{:>0.8f}'.format(volume)+' BTC'), inline=True)
        embed.add_field(name='Base volume', value=('{:>0.0f}'.format(base_volume)+' BCNA'), inline=True)
        embed.add_field(name='Highest bid', value=('{:>0.8f}'.format(high_bid)+' BTC'), inline=True)
        embed.add_field(name='Lowest ask', value=('{:>0.8f}'.format(lowest_ask)+' BTC'), inline=True)
        embed.add_field(name='High price 24h', value=('{:>0.8f}'.format(high_price)+' BTC'), inline=False)
        await ctx.message.channel.send(embed=embed)

# IS USED FOR THE FAUCET FUNCTION. USER SENDS THEIR ADDRESS IT COINS WILL BE DISTRIBUTED AUTOMATICALLY.
# WILL ONLY WORK IF THE USER HAS THE ROLE INVITATIONAL TESTER, THIS WAY WE CAN PREVENT REGULAR USERS TO USE THIS COMMAND.
@client.command(name='claim', hidden=True)
#@commands.has_role('invitational tester')
async def claim(ctx, address=None):
    # If user doesn't send an address with the command, the bot will tell the user he/she has to include it
    if address == None:
        await ctx.message.reply('Address is missing, include your address in the command like this: !claim ADDRESS')
        return
    # This checks if the address is valid
    urlcheck = 'https://lcd-testnet.bitcanna.io/cosmos/auth/v1beta1/accounts/'+address
    try:
        responsecheck = requests.get(urlcheck,headers={'Accept': 'application/json'},)
    except:
        await ctx.message.reply('Something went wrong with API, connection error')

    json_response = responsecheck.json()
    # If the response contains error code 3 this means the address is invalid: malformed bech32
    try:
        code = str(json_response['code'])
    except:
        code = None

    if code == '3':
        await ctx.message.reply(f'{address} is a not valid address, make sure you have copied it properly.')
        return
    # If the response contains error code 5 this means the address is valid and not funded yet. If it doesnt have the error code in the response, the account is valid and already funded.
    # Still, they cant claim twice because of the ClaimedList, so should be ok.
    elif code == '5' or code == None:
        # Checks if user is already in the ClaimedList, if yes then it will tell the user.
        with open('ClaimedList.txt', 'r') as f:
            # Sends a log message to bot-test channel. This enables admins to quickly see who is claiming.
            channel = client.get_channel(807011691401183234)
            await channel.send(f'{ctx.author} / {ctx.author.id} has tried to claim')
            print(str(ctx.author) + ' / ' + str(ctx.author.id) + ' has tried to claim')
            ClaimedUsers = [line.strip() for line in f]
            if str(ctx.author.id) in ClaimedUsers:
                await ctx.message.reply('It looks like you have claimed already! This is not allowed ;) \n' 
                'If this is a mistake, please contact one of our Admins.')
                return
        # Admins will not be added to the ClaimedList, so admins can claim infinitely
        AdminList = ['398132337965269022','805724606324801557','804687093266907186','412915923247169537','431473976146001940','371035381853847552','293167458603237376']
        if str(ctx.author.id) in AdminList :
            pass
        else:
            # If the user is not yet in the Claimedlist, the user will be added of course. So next time he will be unable to claim again.
            with open('ClaimedList.txt', 'a') as f:
                f.write('\n' + str(ctx.author.id))
        urlclaim = 'http://localhost:8000/faucet/claim/'+address
        try:
            # This calls the script of Atmon3r together with the user ADDRESS
            responseclaim = requests.request("GET", urlclaim,headers={'Accept': 'application/json'},)
        except:
            await ctx.message.reply('Something went wrong with the faucet, connection error')
        else:
            if responseclaim.status_code == 200:
                info = json.loads(responseclaim.text)
                tx_hash = info['result']
                # Bot will send a message together with the txhash of the distribution.
                await ctx.message.reply(f'Distribution initiated, you will receive your test coins shortly. \nYour tx hash is https://testnet.ping.pub/bitcanna/tx/{str(tx_hash)}')
            else:
                print ('Data gathering not successful')
                await ctx.message.reply('Data gathering not successful. Unfortunately something went wrong during your claim. Please contact one of our Admins for support')            
    else:
        await ctx.message.reply('Unfortunately something went wrong during your claim. Please contact one of our Admins for support')

@client.command(name='stats', hidden=False)
async def stats(ctx):
    baseurl = 'https://lcd-testnet.bitcanna.io'
    blockslatesturl = baseurl+'/cosmos/base/tendermint/v1beta1/blocks/latest'
    validatorsurl = baseurl+'/cosmos/staking/v1beta1/validators'
    activevalidatorsurl = validatorsurl+'?status=BOND_STATUS_BONDED'
    try:
        responseblocks = requests.get(blockslatesturl,headers={'Accept': 'application/json'},)
        responseval = requests.get(validatorsurl,headers={'Accept': 'application/json'},)
        responseactval = requests.get(activevalidatorsurl,headers={'Accept': 'application/json'},)
    except requests.exceptions.RequestException:
        await ctx.message.reply('Connection error, the API is currently not working. Please try again later.')
    else:
        datablock = responseblocks.json()
        datavalidators = responseval.json()
        dataactval = responseactval.json()
        

        latestblock = datablock['block']['header']['height']
        activevalidators = dataactval['pagination']['total']
        validator_list = datavalidators['validators']
        validator_jailed = []

        for validator in validator_list:
            validator_name = validator['description']['moniker']
            #validator_address = validator['operator_address']

            if validator['jailed'] == True:
                validator_jailed.append(validator_name)

            elif validator['jailed'] == False:
                pass

    embed=discord.Embed(title='BitCanna Testnet', url='https://wallet-testnet.bitcanna.io/', color=0x37BE72)
    embed.set_thumbnail(url='https://i.imgur.com/dpVCzU5.png')
    embed.add_field(name='Latest Block Height', value=latestblock, inline=False)
    embed.add_field(name='Active Validators', value=activevalidators, inline=True)
    embed.add_field(name='Jailed Validators', value=(', '.join(validator_jailed)), inline=True)
    embed.timestamp = datetime.utcnow()
    embed.set_footer(text='Timezone CEST')
    

    await ctx.message.reply(embed=embed)


# EXECUTES THE BOT WITH THE SPECIFIED TOKEN.
client.run(secret)