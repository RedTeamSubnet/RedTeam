

# 🎨 NicheImage - Decentralized Image Generation Network 🌐

## Introduction

### Description
NicheImage is a decentralized network that utilizes the Bittensor protocol to enable distributed image generation. This document serves as a guide for setting up and participating in the network, targeting both validators and miners. It includes essential information on project setup, operation, and contribution.

- 📚 [API Documentation](https://docs.nichetensor.com) (API, Roadmap, Technical Descriptions)
- 🏞️ [Miner and Validator Documentation](https://chestnut-radar-416.notion.site/SN23-SocialTensor-Docs-75202763e797465b88f4d395cb1a14ef)
- 🤖 [Taobot](https://interact.tao.bot/social-tensor)
- 📊 [Subnet Statistics & Playground Showcase](https://studio.nichetensor.com/)

### Incentive Distribution

| Category        | Incentive Distribution | Description                                                                                                        |
|-----------------|------------------------|--------------------------------------------------------------------------------------------------------------------|
| 🧭 GoJourney       | 4%                     | Fixed Image Category                                                                                        |
| 🌀 AnimeV3         | 18%                    | Fixed Image Category                                                                                  |
| ⚔️ JuggernautXL | 15%                    | Fixed Image Category                                                            |
| 🏞️ RealitiesEdgeXL  | 19%                    | Fixed Image Category                                                      |
| 💎 Gemma7b         | 3%                     | Fixed Text Category                                                     |
| 🦙 Llama3_70b      | 5%                     | Fixed Text Category|
| 🏷️ StickerMaker    | 3%                     | Fixed Image Category |
| 🌟 SUPIR    | 8%                     | Fixed Image Category |
| 🌟 Kolors | 10% | Fixed Image Category |
| 🌟🌟 FluxSchnell | 12% | Fixed Image Category |
| **Pixtral_12b** | 1% | Fixed Multimodal Category |
| **OpenGeneral** | 1% | [Open category](/docs/open_category_reward_mechanism.md) |
| **OpenDigitalArt** | 1% | [Open category](/docs/open_category_reward_mechanism.md) |

### Key Features
- 🚀 **Decentralized Image Generation Network**: Incentivizing miners to scale up their computational resources, allowing for up to thousands of generations per minute with sufficient GPU resources.
- 📈 **Volume Commitment**: Miners commit to a model type and generation volume.
- 📊 **Fixed And Open Category**: Miners run fixed model list or their own choice for tailored domain.
- 💰 **Incentivized Volume Rewarding Mechanism**: 
  - `new_reward = (category_score - time_penalty) * (0.6 + 0.4 * volume_scale)`
  - `category_score` is the score unique to each model category. It can be:
    - `matching_result` is 0 or 1 based on the similarity matching result with the reproduction of the validator.
    - `t2i_score` is the score from combination of image quality assessment score and prompt adherence score.
  - `time_penalty = 0.4 * (processing_time / timeout)**3`
  - `volume_scale = max(min(total_volume**0.5 / 1000**0.5, 1), 0)`
- 🌟 **Continuous Improvement**: Introducing new models and features based on usage demand.
- 💵 **Earn as a Validator**: Validators can earn money by sharing their request capacity with miners.

## Setup and Participation

**These guide use `pm2` as a process manager**. If you don't have it installed, you can install it by following the instructions below:
- Install NodeJS Package Manager (npm) [here](https://nodejs.org/en/download/package-manager)
- Install pm2: `npm i pm2 -g`

### For Validators
1. 🛠️ Install the required dependencies and set up the NicheImage validator node.
2. ⚙️ Configure the validator settings, including the amount of TAO to stake.
3. 🚀 Start the validator node and begin processing image generation requests from miners.

Detailed instructions on setting up the NicheImage validator node can be found [here](docs/validator.md).

### For Miners
1. 🛠️ Install the necessary dependencies and set up the NicheImage miner node.
2. 🗂️ Choose the desired model type and specify the generation volume.
3. 🚀 Start the miner node and begin contributing computational resources to the network.

Detailed instructions on setting up the NicheImage miner node can be found [here](docs/miner.md).

## Contribution
We welcome contributions to the NicheImage project! If you have any ideas, bug reports, or feature requests, please open an issue on our GitHub repository. If you'd like to contribute code, please fork the repository and submit a pull request with your changes.

