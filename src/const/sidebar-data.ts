import {
    Brain,
    BrainCircuit,
    ChartNetwork,
    Command,
    FileText,
    Sparkles,
} from "lucide-react";

export const SIDEBAR_DATA = {
    teams: [
        {
            name: "BuddhiAI",
            logo: Brain,
            plan: "AI in Browser",
            url: "/",
        },
        {
            name: "Buddhilive",
            logo: Command,
            plan: "Return to home",
            url: "https://buddhilive.com",
        },
    ],
    navMain: [
        {
            title: "New Chat",
            url: "/chat",
            icon: Sparkles,
        },
        {
            title: "Documents",
            url: "/documents",
            icon: FileText,
        },
        {
            title: "Knowledge Graph",
            url: "/graph",
            icon: ChartNetwork,
        },
        {
            title: "Models",
            url: "/models",
            icon: BrainCircuit,
        },
    ],
    navSecondary: [
        {
            title: "Models",
            url: "/models",
            icon: BrainCircuit,
        },
    ],
    favorites: [
        {
            name: "Project Management & Task Tracking",
            url: "#",
            emoji: "📊",
        },
    ],
    workspaces: [
        {
            name: "Personal Life Management",
            emoji: "🏠",
            pages: [
                {
                    name: "Daily Journal & Reflection",
                    url: "#",
                    emoji: "📔",
                },
            ],
        },
    ],
}