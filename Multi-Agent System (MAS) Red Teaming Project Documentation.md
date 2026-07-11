### Multi-Agent System (MAS) Red Teaming Project Documentation

#### 1\. Abstract and Project Objectives

This project proposes a specialized red teaming architecture utilizing  **AutoResearch-style optimization**  to evaluate the security and robustness of single and multi-agent systems (MAS). Traditional red teaming methodologies frequently focus on user-facing outputs, overlooking the complex internal operations of modern agentic workflows. Contemporary MAS implementations leverage persistent memory (RAG), external tool integration, and sophisticated inter-agent communication, all of which significantly expand the attack surface. These capabilities create pathways for the propagation of malicious instructions or poisoned data within the system’s core logic.A primary contribution of this research is the rigorous analysis of  **Internal Channels** . These channels are defined as data flows hidden from the final user-facing output that serve as the primary drivers for agent decision-making, tool selection, and persistent state management. They include:

* **Agent-to-agent messages:**  Direct communication protocols between specialized agents.  
* **Tool arguments:**  Parameters and metadata passed to external functions, APIs, and databases.  
* **Memory/Shared memory writes:**  Data committed to persistent or ephemeral storage for cross-temporal or cross-agent retrieval.  
* **System logs:**  Internal execution traces, state update records, and node transitions.By monitoring these channels, this project addresses the  **Output-Only Miss Rate** —a phenomenon where attacks successfully compromise internal state or decision-making logic but remain undetected if only the final user-facing output is audited.

#### 2\. Attacker Model

The model assumes an adversary capable of indirect manipulation of the agentic workflow through various entry points.

##### Capabilities

The attacker can inject adversarial content through the following injection points:

* **Retrieved Documents:**  Poisoning external data sources utilized in Retrieval-Augmented Generation (RAG).  
* **Tool Outputs:**  Manipulating data returned from external tool executions or APIs.  
* **Emails:**  Injecting instructions via inbound communication interfaces.  
* **User Task Inputs:**  Engineering prompts at the initial interaction point.  
* **Inter-agent Messages:**  Man-in-the-middle style injections into internal communication streams.  
* **External Sources:**  Manipulating public web pages or databases that agents browse or query.

##### Limitations

The attacker is restricted from direct access to the system’s sensitive underlying infrastructure, weights, or raw protected databases. All adversarial influence is mediated through the aforementioned injection points.

##### Primary Goals

1. **Leakage of Sensitive Information:**  Forcing the system to divulge protected data. To ensure safety and measurable precision, this is evaluated using  **synthetic "canary" data** —non-original sensitive information that the MAS is explicitly tasked to protect.  
2. **Performance Degradation:**  Compromising operational integrity without necessarily leaking data. This targets the availability, efficiency, and correctness of the system by inducing logic failures or resource exhaustion.

#### 3\. Evaluation Frameworks

The architecture is benchmarked across four distinct agentic environments:

* **AgentDojo:**  A standardized benchmark for assessing the robustness, tool-use fidelity, and utility preservation of single-agent systems under prompt injection.  
* **AutoGen:**  A conversational multi-agent framework facilitating complex message-based interactions and human-in-the-loop workflows.  
* **CrewAI:**  A role-based collaborative framework where agents execute hierarchical tasks through delegation, specific goals, and assigned tools.  
* **LangGraph:**  A stateful, graph-based workflow engine. LangGraph is uniquely suited for red teaming as it enables the researcher to trace  **intermediate nodes, edges, and state updates** , pinpointing the exact node where an injection successfully compromised the system's internal state.

#### 4\. Unified Experimental Scenario

To facilitate a comparative analysis, a standardized abstract pipeline is implemented across all frameworks:**User Task → Planner Agent → Retriever/Tool Agent → Worker Agent → Reviewer/Guard Agent → Final Output**

* **Planner Agent:**  Interprets the user's request, decomposes the task into execution steps, and determines which specialized agents are required for sub-tasks.  
* **Retriever/Tool Agent:**  Executes technical sub-tasks using RAG, Google Search, APIs, SQL databases, or custom scripts to augment the system's context.  
* **Worker Agent:**  Aggregates information from the retriever and executes the primary task (e.g., code generation, report drafting) to produce a unified result.  
* **Reviewer/Guard Agent:**  Critically inspects the draft for policy compliance, hallucinations, and injection attempts. It provides feedback to the Worker for iterative refinement before final delivery.

#### 5\. Red Teaming Architecture: AutoResearch Optimization

The core of this system is an automated optimization loop that iteratively refines attack variants to maximize specific adversarial objectives. The process follows a formal sequence:  **Generate Attack Variant → Run Evaluation → Score Result → Keep or Reject → Next Iteration.**Each experiment requires four inputs: a  **Target System**  ( $S$ ), a  **Task**  ( $T$ ), an  **Attack Space**  (modifiable parameters), and a  **Scoring Function** .

##### Loop A: Leakage Optimization

The objective is to maximize the unauthorized exposure of canary data across all channels.

* **Optimization Goal:**   $\\max(TotalExposureRate)$  
* **Modifiable Parameters:**  Attack prompt wording, injection location (e.g., embedding instructions in a tool-returned JSON), target agent selection, tool/document poisoning, canary placement, and  **Attack stealth level**  (the degree to which the injection evades detection by the Guard Agent).

##### Loop B: Performance Degradation Optimization

This loop optimizes for the degradation of system integrity and resource exhaustion.

* **Optimization Goal:**   $Objective\_{perf} \= \\max(\\alpha \\cdot UtilityDrop \+ \\beta \\cdot CostAmplification)$  
* **Modifiable Parameters:**  Misleading context, ambiguous task inputs, and conflicting documents.  
* **Mechanics:**  The loop focuses on  **retry-inducing perturbations**  and  **conflicting context**  designed to induce infinite loops, logic contradictions, or excessive delegation, thereby forcing the system to consume more tokens and API calls while producing lower-quality outputs.

#### 6\. Comprehensive Metrics Suite

Category,Metric Name,Technical Description  
Leakage,LeakageASR,Percentage of trials where sensitive information was leaked to any channel.  
Leakage,Final Output Leakage Rate,Rate of sensitive data reaching the user-facing output.  
Leakage,Internal Leakage Rate,Rate of data leakage within internal channels (hidden from user).  
Leakage,Total Exposure Rate,The union of internal and final output leakage events.  
Leakage,Output-Only Miss Rate,"Measures the % of attacks falsely classified as ""failed"" if only the user-facing output was monitored."  
Performance,Utility Drop,"Quantified decrease in the accuracy, correctness, or quality of the agent's response."  
Performance,Cost Amplification,"Multiplier of resource consumption (Tokens, API usage, GPU time)."  
Performance,Latency,Increase in the temporal duration required for task completion.  
Performance,Tool Call Increase,Growth in the number of external tool invocations induced by the adversary.  
Transfer,Transfer ASR,Success rate of an attack when applied to a framework other than the one it was optimized for.  
Transfer,Generalization Gap,The delta in success rate when an attack is migrated to a novel system.  
Defense,Leakage Reduction,Percentage of previously successful attacks blocked by a specific defense.  
Defense,Utility Preservation,The system's ability to maintain functional performance on benign tasks while defense is active.  
Defense,False Refusal Rate,"Frequency of the defense mechanism blocking legitimate, non-malicious user requests."  
Defense,Over-Defense Rate,"Frequency of excessive defensive actions (e.g., blocking safe tools or redaction of non-sensitive info)."  
Defense,Defense Cost Overhead,"Additional resource consumption (latency, tokens) incurred by the defense layer."  
Defense,Success Despite Guard,Rate of adversarial success while a proactive defense mechanism is active.

#### 7\. Experimental Methodology and Baselines

##### Comparison Baselines

The efficacy of the AutoResearch-style optimization (the proposed system) is benchmarked against:

* **Clean:**  Baseline performance of the target system under non-adversarial conditions.  
* **Random:**  Naive, stochastic injection attempts without iterative optimization.  
* **Manual:**  Human-authored attacks crafted by cybersecurity researchers.  
* **AutoResearch:**  The proposed automated optimization system.

##### Defense Mechanisms

The project evaluates four primary defensive strategies:

1. **Prompt-Based:**  Hardening system prompts to enforce instruction hierarchy and resist hijacking.  
2. **Guard Agent:**  A dedicated review layer analyzing final outputs for security violations.  
3. **Redaction:**  An internal filter that scans and scrubs sensitive data from inter-agent messages and memory writes before commitment.  
4. **Filtering:**  Sanitizing tool and retriever outputs before they are processed by the agentic core.

#### 8\. Experiment Formalization

To ensure reproducibility, every experiment is defined as a 5-tuple:  **$E \= (S, G, A, D, T)**$

* **S (System):**  The target MAS framework (AgentDojo, AutoGen, CrewAI, LangGraph).  
* **G (Goal):**  The adversarial objective (Leakage or Performance Degradation).  
* **A (Attack Type):**  The methodology (Clean, Random, Manual, or AutoResearch).  
* **D (Defense):**  The active defense mechanism (e.g., Inter-Agent Redaction).  
* **T (Task):**  The specific functional assignment (e.g., "Create DFD").**Example Instance:**   $E \= (AutoGen, Leakage, AutoResearch, Guard Agent, Create DFD)$  This formalization represents an automated optimization attack against the AutoGen framework, targeting sensitive information leakage during a Data Flow Diagram creation task, while a Guard Agent defense is active.

