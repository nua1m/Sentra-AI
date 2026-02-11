# AI CYBERSECURITY ASSISTANT FOR THREAT AND VULNERABILITY ANALYSIS

**Muhammad Syahmi Nuaim Bin Anam**  
**21000530**  
**Information Technology**  
**Universiti Teknologi PETRONAS**  
**September 2025**

---

## ABSTRACT

In today's modern world, almost everything is connected to the internet, which means the number of cyber threats like hacking and data breaches is growing fast. While there are good open-source tools like Nmap and Nikto to find weaknesses in systems, they don't work well together. Administrators have to run each tool separately, read through complicated raw data, and figure out how to fix the problems on their own. This messy and manual process is a big problem for students, junior IT staff, and small companies because it takes too much time and skill to do it right.

This project introduces Sentra.AI, a system designed to make cybersecurity easier by automating the work of a "Blue Team" defender. Instead of running separate scans manually, Sentra.AI acts as a single engine that runs both Network Scanning (Nmap) and Web Scanning (Nikto) automatically. It uses AI (Large Language Models) to understand what the user wants to check, runs the right tools for the job, and then explains the results in plain English. Most importantly, it doesn't just find the problems but it also gives clear instructions on how to fix them.

This report covers the progress of building the Sentra.AI prototype, including how the system is designed and how it uses AI to bridge the gap between complicated tools and normal users. The goal is to create a fully automated assistant that lets non-experts run professional-level security checks without needing to be a hacking expert.

---

## CHAPTER 1: INTRODUCTION

### 1.1 Background of Study

Today, almost every organization depends on digital systems, which makes checking for security weaknesses extremely important. However, because there are so many devices and threats are getting smarter, checking security manually is just not effective anymore. Administrators often feel overwhelmed by the repetitive tasks of running diagnostic tools, reading through logs, and checking if patches are applied [1]. While big companies can afford expensive automated solutions, smaller companies and students usually cannot.

To fix this gap, we need accessible tools that can automate these defensive tasks. As noted by Sarker [2], AI has gotten good at detecting threats, but the next big step is automating how we respond to and manage them. Sentra.AI is built on this idea, aiming to move away from "running tools manually" to "letting AI manage the security process."

### 1.2 Problem Statement

Even though there are powerful free tools like Nmap and Nikto, using them effectively is still a struggle for many users due to three main issues:

i. **Tools Don't Work Together**: Administrators have to switch back and forth between different command-line tools, like using Nmap for networks and Nikto for websites, to get a full picture of their security. There is no single system that connects these tools, which leads to messy workflows and wasted time [4]. This fragmentation means users have to manually copy IP addresses from one tool to another, often missing important connections between network flaws and web vulnerabilities.

ii. **Manual Work is Slow and Error-Prone**: Running scans, saving the results, and then trying to connect the dots manually takes a lot of time and effort. Because it is so tedious, many admins don't scan as often as they should, leaving their systems vulnerable for longer periods [5]. Furthermore, interpreting thousands of lines of raw logs leads to "alert fatigue," where critical warnings are missed simply because they are buried in a pile of less important data.

iii. **Finding Problems vs. Fixing Them**: Most scanners are good at telling you what is wrong, like "Port 80 is open", but they rarely tell us how to fix it. Users, especially beginners, are left to research fixes on their own, which is slow and can be risky if they don't know what they are doing. A wrong command copied from the internet could crash a server or open up new security holes, making the problem worse instead of better.

### 1.3 Objectives

The main goal of this project is to build a platform that automates the security scanning process, bringing different tools together under one AI assistant. The specific objectives are:

i. To develop an automated engine that runs open-source tools (Nmap and Nikto) together in a single, streamlined workflow.

ii. To implement an AI logic module that can understand a user's goal (like "Scan this IP") and automatically choose the right tools to use.

iii. To automate the creation of "fix instructions," so the system doesn't just list vulnerabilities but also generates the specific commands needed to remediate them.

### 1.4 Scope of Study

#### 1.4.1 In-Scope (Blue Team Automation)

**Orchestration**: The system will automatically handle the sequence of running Nmap and Nikto scans. This includes passing target IP addresses between tools and ensuring scans run in the correct order (e.g., finding active hosts before scanning for web vulnerabilities).

**Unified Reporting**: It will combine the results from network and web scans into one simple dashboard. The dashboard will categorize findings by severity (High, Medium, Low) and provide a consolidated view of the system's health, rather than separate reports for each tool.

**Remediation Guidance**: The AI will generate specific suggestions for fixing found issues, such as providing the exact command to close a risky port or update a specific service configuration. These suggestions will be tailored to the specific operating system detected during the scan.

**Technology Stack**: The backend is built with Python (FastAPI) to handle the automation logic, while the frontend uses React to provide a user-friendly interface. The AI component utilizes the OpenRouter API to access Large Language Models for interpretation.

#### 1.4.2 Out-of-Scope

**Offensive Automation**: The system will strictly avoid any automated hacking or exploitation features. It will identify vulnerabilities but will not attempt to exploit them (e.g., it will find a SQL injection flaw but will not dump the database).

**Unauthorized Targets**: To prevent misuse, the system uses a verification process similar to Google or SSL providers. Before scanning a public server, the user must prove they own it by uploading a specific verification file (e.g., sentra-verify.txt) to the server. If the file is missing, the scan is blocked.

**Deep System Hardening**: The system currently focuses on finding problems and suggesting basic fixes. Advanced tasks, like automatically changing core operating system files or applying complex security standards may be saved for future updates (FYP 2).

---

## CHAPTER 2: LITERATURE REVIEW

### 2.1 Overview

This chapter looks at how vulnerability management is done today and the problems security teams face. It covers why using separate open-source tools can be messy, why doing everything manually is inefficient, and how Artificial Intelligence (AI) can help manage these tasks instead of just finding threats.

### 2.2 The Challenge of Fragmented Security Tools

One of the biggest headaches in cybersecurity right now is that the tools don't talk to each other. Vulnerability management isn't just one thing, it involves checking the network, scanning websites, and auditing the system itself. Ma [4] points out that administrators usually have to juggle a bunch of different tools like Nmap for networks and other scanners for web apps just to get a full picture of what's going on.

Seara et al. [5] confirmed that while open-source tools are great on their own, they work separately. You can't easily take data from Nmap and feed it into Nikto without doing it manually. This "fragmentation" forces admins to act like human bridges, copying and pasting IP addresses and port numbers between tools. When there isn't a single system to connect everything, it leads to messy workflows and security gaps where threats can slip through. Recent studies by Islam [11] say that Security Orchestration, Automation, and Response (SOAR) frameworks are needed to fix this, but finding simple, affordable solutions for smaller groups is still hard.

### 2.3 The Burden of Manual Operations

As networks get bigger, doing things manually becomes a huge bottleneck. Running scans, waiting for them to finish, and then trying to connect the dots takes a lot of time and effort. Mohamed et al. [3] highlight that this complexity stops non-experts from keeping up with security best practices. Chen and Liu [14] argue that usability isn't just a bonus feature but it's actually a critical part of security. If a tool is badly designed, people will make mistakes or miss vulnerabilities entirely.

On top of that, the output from these tools is usually just a list of problems. They tell you what is wrong but rarely explain how to fix it. This leaves the user with the job of researching the fix themselves which is searching for the right commands to patch a hole. This gap between finding a problem and fixing it is risky because delays mean the system stays vulnerable for longer.

### 2.4 AI as a Security Orchestrator

To fix these issues, recent research suggests that AI should do more than just detect threats; it should help manage the whole process. Khan et al. [6] propose that AI is best used to handle the logic of security operations. Instead of just flagging something weird, an AI model can understand what the user wants to do (like "Secure this server") and automatically pick the right sequence of tools to run.

Sarker [2] supports this idea, arguing that the next big step for AI in cybersecurity is automating how we respond to and manage threats. New advancements in Generative AI, as reviewed by Al-Hawawreh and Moustafa [12], show that Large Language Models (LLMs) can now translate plain English into actual code or commands [13]. By using these models to understand user goals and create fix scripts, systems like Sentra.AI can bridge the gap between finding a problem and fixing it. This supports my project's goal to build an automated engine that doesn't just scan but also guides the user through the fixing process, following the NIST AI Risk Management Framework [15] to keep things safe.

---

## CHAPTER 3: METHODOLOGY

### 3.1 Agile Development Approach

Sentra.AI is being planned and developed using the Agile Methodology, which breaks the project into two main phases corresponding to FYP 1 and FYP 2.

#### 3.1.1 FYP 1: Planning and Design Phase

The current semester (FYP 1) focuses on the foundational work required before full-scale development begins. The activities in this phase include:

i. **Requirement Analysis**: Identifying the specific tools (Nmap, Nikto) and the data they produce.

ii. **System Architecture Design**: defining how the different components (AI, Backend, Frontend) will communicate.

iii. **Feasibility Study**: Evaluating the technical compatibility of the OpenRouter API and the command-line tools to confirm they can be integrated in the next phase.

iv. **Prototype Planning**: Designing the user interface mockups and the database schema.

#### 3.1.2 FYP 2: Development and Implementation Phase

The actual coding and construction of the system will take place in the next semester (FYP 2). This phase will involve:

i. **Backend Development**: Writing the Python code to wrap the security tools.

ii. **Frontend Implementation**: Building the React.js dashboard.

iii. **Integration**: Connecting the AI logic with the scanning engines.

iv. **Testing & Refinement**: Running the system in a controlled environment to fix bugs and improve usability.

### 3.2 System Architecture

The system is designed as an Automated Platform with three distinct layers. This architecture serves as the blueprint for the development work in FYP 2.

#### 3.2.1 The AI Backend (The Brain)

This layer will be built using FastAPI (Python) to control the entire system. It acts as the brain that receives the user's command and decides what to do next.

i. **Intent Analyzer**: It will use the OpenRouter API to figure out what the user wants. For example, if the user says "Check for web vulnerabilities," the AI knows this means it needs to prepare a web scan.

ii. **Task Scheduler**: It will organize the scans in a logical order. For example, it is designed to not run a web scan (Nikto) until the network scan (Nmap) confirms that a web port (like port 80 or 443) is actually open.

#### 3.2.2 The Scanning Engines (The Tools)

This layer contains the actual open-source security tools. The backend will talk to these tools using Python scripts, effectively acting as a robot that types commands for the user.

i. **Network Scanning**: We will use Nmap to find active hosts, open ports, and identify what services are running on the target server.

ii. **Web Scanning**: We will use Nikto to check web servers for common issues like outdated files, dangerous configurations, or known server vulnerabilities.

#### 3.2.3 The Dashboard (The Face)

A React.js frontend will be developed to provide a simple place for the user to see what is happening. Unlike a command line interface which just shows lines of text, this dashboard will combine the results from both tools into one easy-to-read report. It will give a clear picture of the system's security health, categorizing issues by severity so the user knows what to fix first.

### 3.3 Tools and Technologies

The project is planned to use a modern set of tools to ensure it is fast, reliable, and easy to use:

i. **Backend**: Python 3.10 and FastAPI are selected for the server logic because they are fast and work well with automation scripts.

ii. **AI Logic**: The OpenRouter API provides access to Large Language Models (LLMs) that will interpret the scan data.

iii. **Security Tools**: Nmap and Nikto are identified as the core engines for the actual scanning.

iv. **Frontend**: React.js and Tailwind CSS are chosen to build the user interface, ensuring a clean and professional look.

---

## CHAPTER 4: CONCLUSION AND FUTURE WORK

### 4.1 Conclusion

This interim report outlines the foundation for Sentra.AI, a project designed to solve the real-world problems of fragmentation and complexity in cybersecurity tools. By shifting the focus from manual scanning to intelligent automation, this project addresses the "silo problem" where tools like Nmap and Nikto do not communicate with each other. The proposed architecture successfully designs a unified workflow where a single AI assistant orchestrates these tools, making professional-grade security assessments accessible to students and junior administrators.

The work completed in FYP 1, including requirement analysis, system architecture design, and feasibility studies, confirms that integrating open-source command-line tools with Large Language Models (LLMs) is technically viable. The planning phase has defined the necessary logic to bridge the gap between finding security flaws and understanding how to fix them.

### 4.2 Future Work

The next phase of this project (FYP 2) is dedicated entirely to the technical development and implementation of the system designed in FYP 1. The work will focus on achieving the three core objectives:

i. **Development of the Automated Orchestration Engine**:
We will write the backend Python code to physically integrate Nmap and Nikto. This involves building the "wrappers" that allow the system to execute scans automatically and pass data between the network and web scanning modules without human intervention.

ii. **Implementation of AI Logic**:
We will connect the system to the OpenRouter API to implement the decision-making logic. This ensures the system can understand user commands (e.g., "Scan this IP") and intelligently select the correct tools, rather than just running a hard-coded script.

iii. **Building the Remediation Module**:
We will develop the specific feature that translates technical error logs into actionable fix instructions. This involves parsing the vulnerability data and prompting the AI to generate safe, copy-pasteable commands that the user can use to secure their system.

---

## REFERENCES

[1] Cybersecurity Ventures, "2023 Official Cybercrime Report," Cybersecurity Ventures, 2023. [Online]. Available: https://cybersecurityventures.com/cybercrime-report/

[2] I. H. Sarker, "Explainable artificial intelligence for cybersecurity: State-of-the-art, challenges, and research directions," Computers & Security, vol. 127, p. 103123, 2023.

[3] N. Mohamed, M. Aloqaily, and I. A. Elgendy, "Current trends in AI and machine learning for cybersecurity: A state-of-the-art review," Cogent Engineering, vol. 10, no. 1, p. 2272358, 2023.

[4] Y. Ma, "Automated Vulnerability Management," DIVA-Portal, 2023. [Online]. Available: https://www.diva-portal.org/smash/get/diva2:1770617/FULLTEXT01.pdf

[5] J. P. Seara, L. Guimarães, and P. G. Fernandes, "Automation of System Security Vulnerabilities Detection Using Open-Source Software," Electronics, vol. 13, no. 5, p. 873, 2024.

[6] A. S. Khan, K. Sharma, and M. Patel, "Advancing cybersecurity: A comprehensive review of AI-driven technologies," Journal of Big Data, vol. 11, no. 1, 2024.

[7] "AI-Based Software Vulnerability Detection: A Systematic Literature Review," arXiv preprint arXiv:2506.10280, 2025.

[8] R. R. Reddy, "Generative AI in Cybersecurity: A Comprehensive Review of LLM Applications and Vulnerabilities," arXiv preprint arXiv:2405.12750, 2024.

[9] D. Singh, A. Tiwari, and P. K. Verma, "The impact of artificial intelligence on organizational cyber security," Journal of Responsible Technology, vol. 13, p. 100037, 2023.

[10] P. Gupta and H. Zhao, "Leveraging AI for enhanced cybersecurity: A comprehensive review," SN Applied Sciences, vol. 7, no. 3, p. 3773, 2025.

[11] S. Islam, "Security Orchestration, Automation, and Response (SOAR): A Review of the State of the Art," IEEE Access, vol. 11, pp. 10234-10250, 2023.

[12] M. Al-Hawawreh and N. Moustafa, "Generative AI for Cyber Defense: Opportunities and Challenges," IEEE Transactions on Artificial Intelligence, vol. 5, no. 2, pp. 89-102, 2024.

[13] T. Zhang et al., "A Survey on Large Language Models for Code Generation and Analysis," ACM Computing Surveys, vol. 56, no. 4, pp. 1-38, 2024.

[14] K. Chen and J. Liu, "Usability in Cybersecurity: A Human-Centric Approach to Tool Design," International Journal of Human-Computer Interaction, vol. 40, no. 5, pp. 1120-1135, 2024.

[15] NIST, "Artificial Intelligence Risk Management Framework (AI RMF 1.0)," National Institute of Standards and Technology, NIST AI 100-1, 2023.
