<!-- PROJECT SHIELDS -->

[![Gatecoin](https://user-images.githubusercontent.com/35398162/54018436-ee3f6300-4188-11e9-9b4e-0666c44cda53.png)](https://gatecoin.network/)

<h4 align="center">
  Fast, cheap, scalable token transfers for Ethereum
</h4>

#### Quicklinks

[![Python 3.9](https://img.shields.io/pypi/pyversions/gatecoin.svg)](https://gatecoin.readthedocs.io/en/stable/)  [![Chat on Discord](https://img.shields.io/discord/948623129796825109.svg)](https://discord.com/invite/nSQDQBq5FC)

- [Getting Started](#getting-started)
- [Repositories](#repositories)
- [Contact](#contact)

The Gatecoin Network is an off-chain scaling solution, enabling near-instant, low-fee and scalable payments. It's complementary to the Ethereum Blockchain and works with any ERC20 compatible token. The Gatecoin project is work in progress. Its goal is to research state channel technology, define protocols and develop reference implementations.

>**INFO:** The Gatecoin client and smart contracts have been [released for Mainnet](https://medium.com/gatecoin/alderaan-mainnet-release-announcement-7f701e58c236) for the Alderaan release of the Gatecoin Network in May 2020.

The Gatecoin Network is an infrastructure layer on top of the Ethereum Blockchain. While the basic idea is simple, the underlying protocol is quite complex and the implementation non-trivial. Nonetheless the technicalities can be abstracted away, such that developers can interface with a rather simple API to build scalable decentralized applications based on the Gatecoin Network.

[![Gatecoin in a Nutshell](https://user-images.githubusercontent.com/35398162/59496225-46c18300-8e91-11e9-9253-1465f5fd5985.PNG)](https://youtu.be/R1tIy1XgdPw)

## Table of Contents
- [Table of Contents](#table-of-contents)
- [Getting Started](#getting-started)
  - [Learn about Gatecoin](#learn-about-gatecoin)
  - [Use Gatecoin](#use-gatecoin)
- [Specification](#specification)
- [Repositories](#repositories)
  - [Core](#core)
  - [Tools](#tools)
- [Contributing](#contributing)
- [License](#license)
- [Contact](#contact)

## Getting Started

### Learn about Gatecoin

If you haven't used Gatecoin before, you can

* Checkout the [developer portal](http://developer.gatecoin.network)
* Look at the [documentation](https://docs.gatecoin.network/)
* Learn more by watching explanatory [videos](https://www.youtube.com/channel/UCoUP_hnjUddEvbxmtNCcApg)
* Read the blog posts on [Medium](https://medium.com/@gatecoin_network)
* Visit [Awesome-Gatecoin](https://github.com/gatecoin/awesome-gatecoin), a curated list of resources, links, projects, tools and hacks

### Use Gatecoin

If you want to use Gatecoin:
* Read [all installation options](https://gatecoin.readthedocs.io/en/stable/overview_and_guide.html#installation) for Gatecoin
* Read the updated [WebUI tutorial](https://gatecoin.readthedocs.io/en/stable/the-gatecoin-web-interface/the-gatecoin-web-interface.html) to quickly get started doing payments
* Read the thorough guide to [get started with the Gatecoin API](https://gatecoin.readthedocs.io/en/stable/gatecoin-api-1/api-tutorial)

## Specification
Read the [tentative specification for the Gatecoin Network](https://gatecoin-specification.readthedocs.io/en/latest/index.html) to understand in detail how Gatecoin works. It is maintained within [this repository](https://github.com/gatecoin/spec).

## Repositories
The Gatecoin Network is getting created with a set of tools, which are maintained in different repositories.
### Core
- The [solidity smart contracts, libraries and deployment tools](https://github.com/gatecoin/gatecoin) are used to bootstrap a Gatecoin Network on an Ethereum Chain.

- The Gatecoin Python client within the current repository is used to manage payment channels and to make token transfers.

- A [configured matrix server](https://github.com/gatecoin/gatecoin-transport) joins a federation of Matrix servers which is used as the transport layer for the Gatecoin Network.

- The [Service repository](https://github.com/gatecoin/gatecoin-services) contains the code for following services:
    - The Monitoring Service watches open payment channels when the user is not on-line.
    - The Pathfinding service supports users in finding the cheapest or shortest way to route a payment through the network.

- The [Light Client repository](https://github.com/gatecoin/light-client) contains the code for following applications:
    - The Gatecoin Light Client SDK is a Gatecoin Network compatible client written in JavaScript/Typescript.
    - The Gatecoin DApp is a reference implementation of the Gatecoin Light Client SDK.

### Tools
- The [Gatecoin WebUI](https://github.com/gatecoin/webui) is Gatecoin Web User Inteface to manage channels and make token transfers.

- The [Gatecoin Explorer](https://github.com/gatecoin/explorer) visualizes the nodes of the Gatecoin Networks and shows more statistical information.

- The [Gatecoin Wizard](https://github.com/gatecoin/gatecoin-installer) makes it easy to install a Gatecoin client and join the Gatecoin Network.

- The [Scenario Player](https://github.com/gatecoin/scenario-player) is an integration testing tool for the Gatecoin contracts, the Gatecoin client and the services.

- The [Workshop Scripts](https://github.com/gatecoin/workshop) enable workshop facilitators to easily host a Gatecoin Workshop.

## Contributing

Contributions are what make the open source community such an amazing place to learn, inspire, and create. Any contributions you make are **greatly appreciated**.

Also have a look at the [Gatecoin Development Guide](./CONTRIBUTING.md) and the [Gatecoin Developer On-boarding Guide](https://gatecoin.readthedocs.io/en/stable/onboarding.html) for more info.

## License

Distributed under the [MIT License](./LICENSE).

## Contact

Dev Chat: [Discord](https://discord.com/invite/nSQDQBq5FC)

Twitter: [@gatecoin_network](https://twitter.com/gatecoin_network)

Website: [Gatecoin Network](https://gatecoin.network/)

Blog: [Medium](https://medium.com/@gatecoin_network)

Mail: contact@gatecoin.network

*The Gatecoin project is led by Md Sulaiman*

> Disclaimer: Please note, that even though we do our best to ensure the quality and accuracy of the information provided, this publication may contain views and opinions, errors and omissions for which the content creator(s) and any represented organization cannot be held liable. The wording and concepts regarding financial terminology (e.g. "payments", "checks", "currency", "transfer" [of value]) are exclusively used in an exemplary way to describe technological principles and do not necessarily conform to the real world or legal equivalents of these terms and concepts.
