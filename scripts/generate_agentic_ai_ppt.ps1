$ErrorActionPreference = "Stop"

$outputPath = "D:\GenAI_Project_2025\myHealthCoach\docs\AI_AgenticAI_MyHealthCoach_Fundamentals.pptx"

function Add-TitleSlide {
    param(
        $Presentation,
        [string]$Title,
        [string]$Subtitle
    )
    $slide = $Presentation.Slides.Add($Presentation.Slides.Count + 1, 1)
    $slide.Shapes.Title.TextFrame.TextRange.Text = $Title
    $slide.Shapes.Item(2).TextFrame.TextRange.Text = $Subtitle
}

function Add-BulletSlide {
    param(
        $Presentation,
        [string]$Title,
        [string[]]$Bullets
    )
    $slide = $Presentation.Slides.Add($Presentation.Slides.Count + 1, 2)
    $slide.Shapes.Title.TextFrame.TextRange.Text = $Title
    $text = ($Bullets -join "`r`n")
    $slide.Shapes.Item(2).TextFrame.TextRange.Text = $text
}

$ppt = $null
$presentation = $null

try {
    $ppt = New-Object -ComObject PowerPoint.Application
    $ppt.Visible = -1
    $presentation = $ppt.Presentations.Add()

    Add-TitleSlide -Presentation $presentation -Title "AI Agent and Agentic AI Fundamentals" -Subtitle "Definitions, Frameworks, Patterns, and MyHealthCoach Implementation"

    Add-BulletSlide -Presentation $presentation -Title "Learning Objectives" -Bullets @(
        "Understand what AI Agents and Agentic AI are",
        "Differentiate assistants, workflows, and autonomous agents",
        "Learn LangChain, LangGraph, and LangSmith roles",
        "Understand ReAct, Reflection, planning and tool-use patterns",
        "Study a real implementation: MyHealthCoach"
    )

    Add-BulletSlide -Presentation $presentation -Title "What is an AI Agent?" -Bullets @(
        "An AI agent is a software entity that can perceive context, reason, act, and iterate",
        "Core loop: Observe -> Think -> Decide -> Act -> Evaluate",
        "Actions include tool calls, API operations, data retrieval, and responses",
        "Agents are goal-directed, not just single-turn text generators"
    )

    Add-BulletSlide -Presentation $presentation -Title "What is Agentic AI?" -Bullets @(
        "Agentic AI is a system-level design where autonomous behavior drives outcomes",
        "It combines reasoning, memory, tools, planning, and dynamic routing",
        "Often includes multi-step execution and optional multi-agent collaboration",
        "Agentic systems optimize for task completion, not only response fluency"
    )

    Add-BulletSlide -Presentation $presentation -Title "AI Agent vs Agentic AI" -Bullets @(
        "AI Agent: one autonomous unit performing tasks",
        "Agentic AI: architecture and behavior pattern using one or more agents",
        "Single-agent and multi-agent systems can both be agentic",
        "A chatbot is not automatically agentic unless it plans and uses tools intentionally"
    )

    Add-BulletSlide -Presentation $presentation -Title "Agent Types" -Bullets @(
        "Reactive agents: immediate action based on current state",
        "Deliberative agents: plan and reason across steps",
        "Tool-using agents: call search, DB, APIs, and enterprise systems",
        "Multi-agent systems: coordinator and specialists",
        "Human-in-the-loop agents: escalate uncertain or high-risk decisions"
    )

    Add-BulletSlide -Presentation $presentation -Title "Core Building Blocks" -Bullets @(
        "Model: LLM as reasoning engine",
        "Tools: external capabilities and APIs",
        "Memory/State: context over turns and tasks",
        "Planner/Policy: control over next step",
        "Evaluator/Guardrails: quality and safety checks",
        "Observability: traces, metrics, and feedback"
    )

    Add-BulletSlide -Presentation $presentation -Title "Framework Overview" -Bullets @(
        "LangChain: model + prompt + tools + chains for rapid composition",
        "LangGraph: graph/state orchestration for reliable agent workflows",
        "LangSmith: tracing, debugging, experiments, and evaluation",
        "Together: Build -> Orchestrate -> Observe/Evaluate"
    )

    Add-BulletSlide -Presentation $presentation -Title "LangChain Essentials" -Bullets @(
        "Standard interfaces for models, prompts, tools, messages",
        "Tool abstraction for external actions",
        "Reusable components for chains and agents",
        "Great for fast prototyping and modular AI app development"
    )

    Add-BulletSlide -Presentation $presentation -Title "LangGraph Essentials" -Bullets @(
        "Graph-based orchestration with explicit state transitions",
        "Deterministic control for complex, multi-step agent flows",
        "Supports loops, branching, and durable execution",
        "Useful for production-grade agent systems"
    )

    Add-BulletSlide -Presentation $presentation -Title "LangSmith Essentials" -Bullets @(
        "Trace each run: prompts, tool calls, outputs, latency, tokens",
        "Compare experiments across prompt/workflow versions",
        "Run dataset-based evaluations and regressions",
        "Attach structured feedback metrics to run IDs"
    )

    Add-BulletSlide -Presentation $presentation -Title "Reasoning Frameworks and Patterns" -Bullets @(
        "ReAct: interleaves reasoning and actions (Thought + Tool + Observation)",
        "Reflection: critique and improve draft answers before finalizing",
        "Plan-and-Execute: create plan first, then execute step by step",
        "Tree/Graph of Thoughts: branch and compare reasoning paths",
        "Self-Consistency: sample multiple reasoned outputs and choose best"
    )

    Add-BulletSlide -Presentation $presentation -Title "ReAct Pattern" -Bullets @(
        "Best when tool use is required and context is uncertain",
        "Cycle: decide next action, call tool, integrate observation",
        "Improves groundedness and reduces hallucinated details",
        "Tradeoff: higher latency and token cost"
    )

    Add-BulletSlide -Presentation $presentation -Title "Reflection Pattern" -Bullets @(
        "Agent generates draft response and then self-reviews",
        "Checks for missing steps, safety issues, and weak evidence",
        "Can invoke another model or a critic prompt",
        "Tradeoff: better quality vs additional latency"
    )

    Add-BulletSlide -Presentation $presentation -Title "MyHealthCoach Solution Overview" -Bullets @(
        "Domain: personalized health guidance with safe escalation",
        "UI: Streamlit with user context (age, gender, weight, zip/pincode)",
        "Orchestration: LangGraph state flow",
        "Reasoning: supervisor ReAct + specialist ReAct advisors",
        "Data/Tools: user context, summaries, RAG docs, nearby doctor lookup",
        "Observability/Eval: LangSmith + custom evaluation criteria"
    )

    Add-BulletSlide -Presentation $presentation -Title "MyHealthCoach Agent Architecture" -Bullets @(
        "Supervisor agent routes user intent to relevant specialists",
        "Specialists: wellness, fitness, dietitian, mental, maternal, women health",
        "Doctor lookup router: US zip -> NPI API; India pincode -> Nominatim + Overpass",
        "Final synthesis combines specialist outputs into actionable guidance",
        "Safety-first behavior: non-diagnostic advice and escalation notes"
    )

    Add-BulletSlide -Presentation $presentation -Title "Implementation Walkthrough" -Bullets @(
        "1) Capture user query and profile in Streamlit",
        "2) Build initial state and enrich user context",
        "3) Supervisor ReAct selects specialist tools",
        "4) Domain ReAct retrieves data and forms facts",
        "5) Optional doctor lookup based on risk/need",
        "6) Final response rendered + live evaluation score",
        "7) Batch regressions run on fixed prompt dataset",
        "8) Feedback mapped and submitted to LangSmith runs"
    )

    Add-BulletSlide -Presentation $presentation -Title "Evaluation and Performance" -Bullets @(
        "Criteria: routing accuracy, tool grounding, actionability, safety, doctor lookup, latency",
        "Outputs: overall weighted score + pass/fail + per-check details",
        "Batch regression: 20 prompts for consistency checks",
        "LangSmith feedback keys enable experiment comparison over time"
    )

    Add-BulletSlide -Presentation $presentation -Title "Best Practices and Guardrails" -Bullets @(
        "Use explicit system policies for medical safety boundaries",
        "Prefer tool-grounded responses over free-form assumptions",
        "Track latency/cost and optimize tool call frequency",
        "Keep human escalation paths for high-risk medical scenarios",
        "Continuously evaluate with representative datasets"
    )

    Add-BulletSlide -Presentation $presentation -Title "Class Discussion and Lab Tasks" -Bullets @(
        "Task 1: Convert a Q and A bot into a simple ReAct agent",
        "Task 2: Add one external tool and evaluate grounding",
        "Task 3: Add reflection step and compare quality/latency",
        "Task 4: Design 10 evaluation prompts for one domain",
        "Task 5: Review traces and propose optimization changes"
    )

    Add-BulletSlide -Presentation $presentation -Title "Thank You" -Bullets @(
        "You now have a practical map from AI agent basics to production agentic systems",
        "Next step: run the MyHealthCoach demo and inspect traces in LangSmith"
    )

    $presentation.SaveAs($outputPath)
    $presentation.Close()
    $ppt.Quit()

    Write-Output "PPTX created: $outputPath"
}
catch {
    if ($presentation -ne $null) { $presentation.Close() }
    if ($ppt -ne $null) { $ppt.Quit() }
    throw
}
