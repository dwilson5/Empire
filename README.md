![Empire](https://user-images.githubusercontent.com/20302208/70022749-1ad2b080-154a-11ea-9d8c-1b42632fd9f9.jpg)

[1]: https://www.bc-security.org/blog

![GitHub Release](https://img.shields.io/github/v/release/BC-SECURITY/Empire)
![GitHub contributors](https://img.shields.io/github/contributors/BC-SECURITY/Empire)
![GitHub commit activity](https://img.shields.io/github/commit-activity/m/BC-SECURITY/Empire)
![GitHub stars](https://img.shields.io/github/stars/BC-SECURITY/Empire)
![GitHub](https://img.shields.io/github/license/BC-Security/Empire)
[![Twitter URL](https://img.shields.io/twitter/url/https/twitter.com/fold_left.svg?style=flat)](https://twitter.com/BCSecurity1)
[![Discord](https://img.shields.io/discord/716165691383873536)](https://discord.gg/P8PZPyf)

Keep up-to-date on our blog at [https://www.bc-security.org/blog][1]

[Documentation](https://bc-security.gitbook.io/empire-wiki/)

# Empire
Empire 4 is a post-exploitation framework that includes a pure-PowerShell Windows agents, Python 3.x Linux/OS X agents, 
and C# agents. It is the merger of the previous PowerShell Empire and Python EmPyre projects. The framework offers 
cryptologically-secure communications and flexible architecture.

On the PowerShell side, Empire implements the ability to run PowerShell agents without needing powershell.exe, rapidly 
deployable post-exploitation modules ranging from key loggers to Mimikatz, and adaptable communications to evade 
network detection, all wrapped up in a usability-focused framework. PowerShell Empire premiered at 
[BSidesLV in 2015](https://www.youtube.com/watch?v=Pq9t59w0mUI) and Python EmPyre premiered at HackMiami 2016. 
BC Security presented updates to further evade Microsoft Antimalware Scan Interface (AMSI) and JA3/S signatures at 
[DEF CON 27](https://github.com/BC-SECURITY/DEFCON27).

Empire relies heavily on the work from several other projects for its underlying functionality. We have tried to call 
out a few of those people we've interacted with heavily [here](http://www.powershellempire.com/?page_id=2) and have 
included author/reference link information in the source of each Empire module as appropriate. If we have failed to 
properly cite existing or prior work, please let us know at Empire@BC-Security.org.

Empire is currently being developed and maintained by [@Cx01N](https://twitter.com/Cx01N_), 
[@Hubbl3](https://twitter.com/_Hubbl3), & [@Vinnybod](https://twitter.com/_vinnybod). While the original Empire project is
no longer maintained, this fork is maintained by [@bcsecurity1](https://twitter.com/BCSecurity1). Please reach out to 
us on our [Discord](https://discord.gg/P8PZPyf) if you have any questions or want to talk about offensive security.

Thank you to the original team of developers: [@harmj0y](https://twitter.com/harmj0y), 
[@sixdub](https://twitter.com/sixdub), [@enigma0x3](https://twitter.com/enigma0x3), 
[@rvrsh3ll](https://twitter.com/424f424f), [@killswitch_gui](https://twitter.com/killswitch_gui), & 
[@xorrior](https://twitter.com/xorrior)

## Sponsors
[<img src="https://user-images.githubusercontent.com/20302208/185247407-46b00d46-0468-4600-9c0d-4efeedc38b3b.png" height="100"/>](https://www.kali.org/) &emsp; &emsp; &emsp;
[<img src="https://user-images.githubusercontent.com/20302208/185246508-56f4f574-5a06-4a2c-ac62-320922588dcf.png" width="100"/>](https://www.sans.org/cyber-security-courses/red-team-operations-adversary-emulation/) &emsp; &emsp; &emsp;
[<img src="https://user-images.githubusercontent.com/20302208/113086242-219d2200-9196-11eb-8c91-84f19c646873.png" width="100"/>](https://kovert.no/)

## Release Notes

Please see our [Releases](https://github.com/BC-SECURITY/Empire/releases) or [Changelog](/changelog) page for detailed release notes.

###  Quickstart
Empire 4 introduces a new server and client architecture which requires running each in separate terminals. 
Check out the [Installation Page](https://bc-security.gitbook.io/empire-wiki/quickstart/installation) for install instructions.

#### Server

```bash
# Start Server
./ps-empire server

# Help
./ps-empire server -h
```

#### Client

```bash
# Start Client
./ps-empire client

# Help
./ps-empire client -h
```

Check out the [Empire Docs](https://bc-security.gitbook.io/empire-wiki/) for more instructions on installing and using with Empire.
For a complete list of the 4.0 changes, see the [changelog](./changelog).

Join us in [our Discord](https://discord.gg/P8PZPyf) to with any comments, questions, concerns, or problems!

## Starkiller
<div align="center"><img width="125" src="https://github.com/BC-SECURITY/Starkiller/blob/master/src/assets/icon.png"></div>

[Starkiller](https://github.com/BC-SECURITY/Starkiller) is a GUI for PowerShell Empire that interfaces remotely with Empire via its API. Starkiller can be ran as a replacement for the Empire client or in a mixed environment with Starkiller and Empire clients.

## Contribution Rules
See [Contributing](./.github/CONTRIBUTING.md)

## Official Discord Channel
<p align="center">
<a href="https://discord.gg/P8PZPyf">
<img src="https://discordapp.com/api/guilds/716165691383873536/widget.png?style=banner3"/>
</p>
