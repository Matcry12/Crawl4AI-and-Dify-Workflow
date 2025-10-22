# EOS Network: Local Project Setup with CLI

**Category**: guide
**Mode**: full-doc
**Created**: 2025-10-22T23:04:29.045947
**Updated**: 2025-10-22T23:04:29.045958
**Merged Topics**: 1
  - EOS Network: Local Project Setup with CLI (merged: 2025-10-22T23:04:29.045960)

---

## EOS Network: Local Project Setup with CLI

This guide details how to set up a new EOS Network project locally using the command-line interface (CLI) for contract and frontend development. This process is crucial for developers transitioning from the Web IDE to a full local development workflow.

### Initializing a New Project with the CLI

To initialize a new EOS Network project, use the following command in your terminal:

`npm create vaulta@latest myproject`

This command will initiate the project creation process. You will be guided through a series of prompts to configure your project. Based on your selections, the generated project can result in either a template project with pre-configured components or a barebones setup.

### Project Structure and Components

The generated EOS Network project typically includes:

*   A simple smart contract.
*   Associated tests for the smart contract.
*   Deployment scripts to facilitate the deployment process.
*   Support for popular frontend frameworks, with options to choose from:
    *   SvelteKit
    *   Next.js
    *   Nuxt
