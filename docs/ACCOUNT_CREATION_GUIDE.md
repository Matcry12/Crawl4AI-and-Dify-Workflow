# How to Create an Account on EOS/Vaulta

A comprehensive step-by-step guide to creating your first EOS account on the Vaulta platform.

---

## Table of Contents
- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Step 1: Understanding EOS Accounts](#step-1-understanding-eos-accounts)
- [Step 2: Choose Your Method](#step-2-choose-your-method)
- [Step 3: Generate Key Pair](#step-3-generate-key-pair)
- [Step 4: Select Account Name](#step-4-select-account-name)
- [Step 5: Register Your Account](#step-5-register-your-account)
- [Step 6: Verify Your Account](#step-6-verify-your-account)
- [Troubleshooting](#troubleshooting)

---

## Overview

An EOS account is a human-readable name (like `alice.vaulta`) that serves as your identity on the blockchain. Unlike traditional wallets with long hexadecimal addresses, EOS accounts are easy to remember and share.

**What you'll learn:**
- How to create an account on EOS/Vaulta
- Understanding public/private key pairs
- Account naming rules and conventions
- Managing account resources (RAM, CPU, NET)

---

## Prerequisites

Before creating your account, ensure you have:

- [ ] A secure device (computer or smartphone)
- [ ] Internet connection
- [ ] Basic understanding of blockchain concepts
- [ ] A secure location to store your private keys (password manager recommended)

**Important:** You'll need to pay for account creation (small fee in EOS tokens) or use a free account creation service.

---

## Step 1: Understanding EOS Accounts

### What is an EOS Account?

An EOS account consists of:
- **Account Name:** 12-character human-readable identifier (e.g., `alice.vaulta`)
- **Owner Key:** Master key with full control
- **Active Key:** Key for daily transactions
- **Permissions:** Customizable permission structure

### Account vs Wallet
- **Account:** Your identity on the blockchain (public)
- **Wallet:** Software that stores your private keys (private)

### Key Properties
- **Unique:** Each account name can only exist once
- **Permanent:** Cannot be deleted (can be transferred)
- **Hierarchical:** Supports sub-accounts (e.g., `alice.game.vaulta`)

---

## Step 2: Choose Your Method

### Method A: Vaulta Web IDE (Recommended for Developers)

**Best for:** Smart contract developers, testnet usage

1. Visit: https://vaulta.com/
2. Click "Create Account" button
3. Follow the web IDE wizard
4. Automatically creates testnet account

**Pros:**
- ✅ Free for testnet
- ✅ Integrated development environment
- ✅ Instant setup

**Cons:**
- ❌ Testnet only by default
- ❌ Requires mainnet migration later

---

### Method B: EOS Wallet App (Recommended for Users)

**Best for:** General users, token holders

**Popular wallets:**
- **Anchor Wallet** (Desktop & Mobile) - Most popular
- **Wombat** (Mobile) - User-friendly
- **TokenPocket** (Mobile) - Multi-chain support

**Steps for Anchor Wallet:**

1. Download from https://greymass.com/anchor
2. Install and launch
3. Click "Create Account"
4. Choose network (Mainnet or Testnet)
5. Follow account creation flow

---

### Method C: Command Line (Advanced)

**Best for:** Node operators, advanced users

**Requirements:**
- `cleos` CLI tool installed
- Access to EOS node
- Existing account with EOS tokens

```bash
# Install cleos (part of EOSIO software)
# See: https://github.com/EOSIO/eos

# Generate keys first (see Step 3)
cleos create key --to-console

# Then create account (requires existing account)
cleos system newaccount \
  --stake-net "0.1000 EOS" \
  --stake-cpu "0.1000 EOS" \
  --buy-ram-kbytes 8 \
  creator_account new_account \
  owner_public_key active_public_key
```

---

## Step 3: Generate Key Pair

Your account needs cryptographic key pairs for security.

### Option 1: Wallet App (Easiest)

Most wallet apps generate keys automatically during setup.

**Example with Anchor:**
1. Open Anchor Wallet
2. Click "New Account"
3. Choose "Generate Keys"
4. **Write down your 12-word mnemonic phrase**
5. Store securely (never share!)

---

### Option 2: Vaulta Web IDE

```javascript
// In Vaulta Web IDE console:
const { PrivateKey } = require('eosjs/dist/eosjs-ecc');

// Generate owner key
const ownerPrivateKey = await PrivateKey.randomKey();
const ownerPublicKey = ownerPrivateKey.toPublic().toString();

// Generate active key
const activePrivateKey = await PrivateKey.randomKey();
const activePublicKey = activePrivateKey.toPublic().toString();

console.log('Owner Private Key:', ownerPrivateKey.toString());
console.log('Owner Public Key:', ownerPublicKey);
console.log('Active Private Key:', activePrivateKey.toString());
console.log('Active Public Key:', activePublicKey);
```

**⚠️ Security Warning:**
- Save private keys immediately
- Never share private keys
- Use password manager or hardware wallet
- Create backup in secure location

---

### Option 3: Command Line

```bash
# Generate owner key pair
cleos create key --to-console
# Output:
# Private key: 5KQwrPbwdL6PhXujxW37FSSQZ1JiwsST4cqQzDeyXtP79zkvFD3
# Public key:  EOS6MRyAjQq8ud7hVNYcfnVPJqcVpscN5So8BhtHuGYqET5GDW5CV

# Generate active key pair
cleos create key --to-console
# Output:
# Private key: 5JYf...
# Public key:  EOS7g...

# Save these securely!
```

---

## Step 4: Select Account Name

### Naming Rules

**Format:** `[a-z1-5]{12}` (exactly 12 characters)

**Allowed characters:**
- Lowercase letters: `a-z`
- Numbers: `1-5` (NOT 0, 6-9)

**Examples:**
- ✅ Valid: `alice1234567`, `bobsmith1111`, `cryptotrader`
- ❌ Invalid: `Alice123` (uppercase), `bob` (too short), `user6789` (invalid numbers)

### Premium Names

Some account names may require higher fees:
- Short names (< 12 chars) often require bidding
- Vanity names may cost more
- Check availability before proceeding

### Checking Availability

**Using Vaulta Web IDE:**
```javascript
const { JsonRpc } = require('eosjs');
const rpc = new JsonRpc('https://api.vaulta.com');

async function checkAccount(accountName) {
  try {
    const account = await rpc.get_account(accountName);
    console.log('Account exists:', account);
  } catch (e) {
    console.log('Account available!');
  }
}

checkAccount('alice1234567');
```

**Using Command Line:**
```bash
cleos -u https://api.vaulta.com get account alice1234567
# If not found, account is available
```

---

## Step 5: Register Your Account

### Method A: Vaulta Web IDE

1. Open https://vaulta.com/
2. Navigate to "Accounts" section
3. Click "Create New Account"
4. Fill in the form:
   ```
   Account Name: alice1234567
   Owner Public Key: EOS6MRy...
   Active Public Key: EOS7g...
   Network: Testnet
   ```
5. Click "Create Account"
6. Wait for confirmation (usually 1-2 seconds)

**Cost:** Free on testnet

---

### Method B: Anchor Wallet

1. Open Anchor Wallet
2. Click "Create Account"
3. Choose network (Mainnet/Testnet)
4. Enter desired account name
5. Review costs:
   - Account creation fee: ~0.5 EOS
   - RAM: ~3 KB minimum
   - CPU/NET: Staked resources
6. Confirm payment method
7. Complete creation

**Total cost:** Approximately 1-2 EOS (mainnet)

---

### Method C: Account Creation Service

**Free services (testnet):**
- EOS Testnet Faucet: https://faucet.testnet.eos.io/
- Jungle Testnet: https://monitor.jungletestnet.io/

**Paid services (mainnet):**
- EOS Account Creator: https://eos-account-creator.com/
- Zeos: https://www.zeos.co/

**Steps (using faucet):**
1. Visit testnet faucet URL
2. Enter account name
3. Paste owner public key
4. Paste active public key
5. Complete CAPTCHA
6. Click "Create Account"
7. Receive confirmation email

---

### Method D: Command Line (Advanced)

**Prerequisites:**
- Existing EOS account (creator)
- Sufficient EOS tokens
- Private key of creator account

```bash
# Set variables
CREATOR_ACCOUNT="youraccount"
NEW_ACCOUNT="alice1234567"
OWNER_PUBLIC_KEY="EOS6MRyAjQq8ud7hVNYcfnVPJqcVpscN5So8BhtHuGYqET5GDW5CV"
ACTIVE_PUBLIC_KEY="EOS7g..."

# Create account
cleos -u https://api.vaulta.com system newaccount \
  $CREATOR_ACCOUNT \
  $NEW_ACCOUNT \
  $OWNER_PUBLIC_KEY \
  $ACTIVE_PUBLIC_KEY \
  --stake-net "0.1000 EOS" \
  --stake-cpu "0.1000 EOS" \
  --buy-ram-kbytes 8 \
  -p $CREATOR_ACCOUNT@active

# Expected output:
# executed transaction: abc123...
# account creation successful
```

**Resource breakdown:**
- `--stake-net`: Network bandwidth (0.1 EOS)
- `--stake-cpu`: CPU resources (0.1 EOS)
- `--buy-ram-kbytes`: RAM for account (8 KB ≈ 0.5 EOS)

---

## Step 6: Verify Your Account

### Check Account Exists

**Vaulta Web IDE:**
```javascript
const { JsonRpc } = require('eosjs');
const rpc = new JsonRpc('https://api.vaulta.com');

async function verifyAccount(accountName) {
  try {
    const account = await rpc.get_account(accountName);
    console.log('✅ Account created successfully!');
    console.log('Account details:', account);
    console.log('RAM:', account.ram_quota, 'bytes');
    console.log('CPU:', account.cpu_limit);
    console.log('NET:', account.net_limit);
    return true;
  } catch (e) {
    console.log('❌ Account not found:', e.message);
    return false;
  }
}

verifyAccount('alice1234567');
```

**Command Line:**
```bash
cleos -u https://api.vaulta.com get account alice1234567
```

**Expected output:**
```
created: 2025-01-15T10:30:00.000
permissions:
     owner     1:    1 EOS6MRyAjQq8ud7hVNYcfnVPJqcVpscN5So8BhtHuGYqET5GDW5CV
        active     1:    1 EOS7g...
memory:
     quota:     8.19 KiB    used:     2.66 KiB

net bandwidth:
     staked:          0.1000 EOS           (total stake delegated from account to self)
     delegated:       0.0000 EOS           (total staked delegated to account from others)
     used:                 0 bytes
     available:        1.45 MiB
     limit:            1.45 MiB

cpu bandwidth:
     staked:          0.1000 EOS           (total stake delegated from account to self)
     delegated:       0.0000 EOS           (total staked delegated to account from others)
     used:                 0 us
     available:        290.4 ms
     limit:            290.4 ms
```

---

### Test Transaction

Send a small transaction to verify your keys work:

```bash
# Transfer 0.0001 EOS to yourself
cleos -u https://api.vaulta.com transfer \
  alice1234567 alice1234567 "0.0001 EOS" "test transaction" \
  -p alice1234567@active

# Expected: success
```

---

### Import to Wallet

**Anchor Wallet:**
1. Open Anchor
2. Click "Import Account"
3. Enter account name: `alice1234567`
4. Enter private key (active key)
5. Click "Import"
6. Verify account appears in wallet

**Vaulta Web IDE:**
1. Go to "Wallet" tab
2. Click "Import Keys"
3. Paste private keys
4. Associate with account name
5. Save wallet

---

## Troubleshooting

### Common Errors

#### Error: "Account name already exists"
**Solution:**
- Choose different account name
- Check availability first
- Consider adding numbers/variations

#### Error: "Invalid account name"
**Solution:**
- Ensure exactly 12 characters
- Use only `a-z` and `1-5`
- No uppercase, no special characters
- Examples: `alice1234567` ✅, `Alice_123` ❌

#### Error: "Insufficient RAM"
**Solution:**
```bash
# Buy more RAM
cleos -u https://api.vaulta.com system buyram \
  alice1234567 alice1234567 "0.5 EOS" \
  -p alice1234567@active
```

#### Error: "CPU/NET exhausted"
**Solution:**
```bash
# Stake more for CPU
cleos -u https://api.vaulta.com system delegatebw \
  alice1234567 alice1234567 \
  "0.0000 EOS" "0.5000 EOS" \
  -p alice1234567@active

# Stake more for NET
cleos -u https://api.vaulta.com system delegatebw \
  alice1234567 alice1234567 \
  "0.5000 EOS" "0.0000 EOS" \
  -p alice1234567@active
```

#### Error: "Transaction expired"
**Solution:**
- Check internet connection
- Ensure system time is accurate
- Try again (transaction may have succeeded)

---

### Security Best Practices

1. **Private Key Storage:**
   - ✅ Use hardware wallet (Ledger, Trezor)
   - ✅ Use password manager (1Password, Bitwarden)
   - ✅ Write down on paper, store in safe
   - ❌ Never store in plain text files
   - ❌ Never share via email/messaging
   - ❌ Never screenshot private keys

2. **Two-Key System:**
   - Use **owner key** only for critical operations
   - Use **active key** for daily transactions
   - Keep owner key offline (cold storage)

3. **Account Recovery:**
   - Save account name securely
   - Backup all private keys
   - Test recovery process on testnet
   - Document permission structure

---

### Getting Help

**Official Resources:**
- EOS Documentation: https://docs.eosnetwork.com/
- Vaulta Support: https://vaulta.com/support
- Telegram: https://t.me/EOSNetworkFoundation
- Discord: https://discord.gg/eosnetwork

**Community Forums:**
- Reddit: r/eos
- Stack Exchange: eosio.stackexchange.com
- GitHub: https://github.com/EOSIO/eos/issues

---

## Next Steps

After creating your account:

1. **Fund Your Account:**
   - Buy EOS tokens from exchange
   - Transfer to your new account
   - Ensure sufficient resources (RAM/CPU/NET)

2. **Secure Your Account:**
   - Review and customize permissions
   - Set up multi-signature if needed
   - Enable 2FA on wallet apps

3. **Start Using:**
   - Explore dApps on EOS
   - Try sending transactions
   - Learn about smart contracts
   - Join the developer community

4. **Learn More:**
   - [Smart Contract Development](https://docs.eosnetwork.com/docs/latest/quick-start/)
   - [Account Permissions](https://docs.eosnetwork.com/docs/latest/core-concepts/accounts-and-permissions)
   - [Resource Management](https://docs.eosnetwork.com/docs/latest/core-concepts/resources)

---

## Summary Checklist

- [ ] Understand what an EOS account is
- [ ] Choose creation method (Wallet/CLI/Web IDE)
- [ ] Generate secure key pairs
- [ ] Select available account name
- [ ] Create account on network
- [ ] Verify account exists
- [ ] Import keys to wallet
- [ ] Test transaction
- [ ] Backup private keys securely
- [ ] Explore EOS ecosystem

**Congratulations! You now have an EOS account on Vaulta!** 🎉

---

**Document Version:** 1.0
**Last Updated:** 2025-01-15
**Author:** EOS Network Foundation
**License:** CC BY 4.0
