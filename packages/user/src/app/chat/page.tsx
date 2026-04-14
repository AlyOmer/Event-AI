"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import {
    Send,
    Bot,
    User,
    Loader2,
    Sparkles,
    Calendar,
    Search,
    ShoppingBag,
    ClipboardList,
    Zap,
    MessageSquare,
    ChevronDown,
} from "lucide-react";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

type Message = {
    id: string;
    role: "user" | "assistant";
    content: string;
    agent?: string;
    timestamp: Date;
};

type QuickAction = {
    icon: React.ElementType;
    label: string;
    prompt: string;
    color: string;
};

const QUICK_ACTIONS: QuickAction[] = [
    {
        icon: Calendar,
        label: "Plan Event",
        prompt: "I want to plan an event",
        color: "from-violet-500 to-purple-600",
    },
    {
        icon: Search,
        label: "Find Vendors",
        prompt: "Help me find vendors for my event",
        color: "from-blue-500 to-cyan-600",
    },
    {
        icon: ShoppingBag,
        label: "Book Service",
        prompt: "I want to book a vendor service",
        color: "from-emerald-500 to-teal-600",
    },
    {
        icon: ClipboardList,
        label: "My Bookings",
        prompt: "Show me my bookings",
        color: "from-amber-500 to-orange-600",
    },
];

/* ------------------------------------------------------------------ */
/*  Markdown-lite renderer (no deps)                                   */
/* ------------------------------------------------------------------ */

function renderMarkdown(text: string) {
    const lines = text.split("\n");
    const elements: React.ReactNode[] = [];
    let key = 0;

    for (let i = 0; i < lines.length; i++) {
        let line = lines[i];

        // Headers
        if (line.startsWith("### ")) {
            elements.push(
                <h4 key={key++} className="font-semibold text-sm mt-3 mb-1 text-white/90">
                    {processInline(line.slice(4))}
                </h4>
            );
            continue;
        }
        if (line.startsWith("## ")) {
            elements.push(
                <h3 key={key++} className="font-bold text-base mt-3 mb-1 text-white/95">
                    {processInline(line.slice(3))}
                </h3>
            );
            continue;
        }
        if (line.startsWith("# ")) {
            elements.push(
                <h2 key={key++} className="font-bold text-lg mt-3 mb-2 text-white">
                    {processInline(line.slice(2))}
                </h2>
            );
            continue;
        }

        // Horizontal rule
        if (line.match(/^-{3,}$/) || line.match(/^\*{3,}$/)) {
            elements.push(<hr key={key++} className="border-white/10 my-3" />);
            continue;
        }

        // Bullet list items
        if (line.match(/^[\s]*[-•*]\s/)) {
            elements.push(
                <div key={key++} className="flex items-start gap-2 ml-2 my-0.5">
                    <span className="text-white/40 mt-1.5 text-[8px]">●</span>
                    <span className="text-sm leading-relaxed">{processInline(line.replace(/^[\s]*[-•*]\s/, ""))}</span>
                </div>
            );
            continue;
        }

        // Numbered list items
        if (line.match(/^[\s]*\d+\.\s/)) {
            const match = line.match(/^[\s]*(\d+)\.\s(.*)$/);
            if (match) {
                elements.push(
                    <div key={key++} className="flex items-start gap-2 ml-2 my-0.5">
                        <span className="text-white/50 text-xs font-medium min-w-[18px]">{match[1]}.</span>
                        <span className="text-sm leading-relaxed">{processInline(match[2])}</span>
                    </div>
                );
                continue;
            }
        }

        // Empty line
        if (line.trim() === "") {
            elements.push(<div key={key++} className="h-2" />);
            continue;
        }

        // Regular paragraph
        elements.push(
            <p key={key++} className="text-sm leading-relaxed my-0.5">
                {processInline(line)}
            </p>
        );
    }

    return <>{elements}</>;
}

function processInline(text: string): React.ReactNode {
    const parts: React.ReactNode[] = [];
    let remaining = text;
    let key = 0;

    while (remaining.length > 0) {
        // Bold **text**
        const boldMatch = remaining.match(/\*\*(.+?)\*\*/);
        // Inline code `text`
        const codeMatch = remaining.match(/`([^`]+)`/);
        // Italic *text*
        const italicMatch = remaining.match(/(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)/);

        const matches = [
            boldMatch ? { type: "bold", match: boldMatch } : null,
            codeMatch ? { type: "code", match: codeMatch } : null,
            italicMatch ? { type: "italic", match: italicMatch } : null,
        ]
            .filter(Boolean)
            .sort((a, b) => (a!.match.index! - b!.match.index!)) as {
                type: string;
                match: RegExpMatchArray;
            }[];

        if (matches.length === 0) {
            parts.push(<span key={key++}>{remaining}</span>);
            break;
        }

        const first = matches[0];
        const idx = first.match.index!;

        if (idx > 0) {
            parts.push(<span key={key++}>{remaining.slice(0, idx)}</span>);
        }

        if (first.type === "bold") {
            parts.push(
                <strong key={key++} className="font-semibold text-white">
                    {first.match[1]}
                </strong>
            );
        } else if (first.type === "code") {
            parts.push(
                <code
                    key={key++}
                    className="bg-white/10 text-emerald-300 px-1.5 py-0.5 rounded text-xs font-mono"
                >
                    {first.match[1]}
                </code>
            );
        } else if (first.type === "italic") {
            parts.push(
                <em key={key++} className="italic text-white/80">
                    {first.match[1]}
                </em>
            );
        }

        remaining = remaining.slice(idx + first.match[0].length);
    }

    return <>{parts}</>;
}

/* ------------------------------------------------------------------ */
/*  Agent badge colour map                                             */
/* ------------------------------------------------------------------ */

const AGENT_COLORS: Record<string, string> = {
    TriageAgent: "from-violet-500 to-purple-600",
    VendorDiscoveryAgent: "from-blue-500 to-cyan-500",
    SchedulerAgent: "from-amber-500 to-orange-500",
    ApprovalAgent: "from-emerald-500 to-green-500",
    MailAgent: "from-pink-500 to-rose-500",
    BookingAgent: "from-teal-500 to-emerald-500",
    EventPlannerAgent: "from-indigo-500 to-violet-500",
    OrchestratorAgent: "from-fuchsia-500 to-pink-500",
    "AI Assistant": "from-slate-500 to-gray-500",
    "Gemini AI": "from-blue-400 to-indigo-500",
    "Demo Mode": "from-gray-500 to-gray-600",
    System: "from-red-500 to-orange-500",
};

function getAgentColor(agent?: string) {
    if (!agent) return "from-slate-500 to-gray-500";
    return AGENT_COLORS[agent] || "from-slate-500 to-gray-500";
}

function getAgentDisplayName(agent?: string) {
    if (!agent) return "AI";
    return agent
        .replace("Agent", "")
        .replace(/([A-Z])/g, " $1")
        .trim();
}

/* ------------------------------------------------------------------ */
/*  Chat Page Component                                                */
/* ------------------------------------------------------------------ */

export default function ChatPage() {
    const [messages, setMessages] = useState<Message[]>([]);
    const [input, setInput] = useState("");
    const [isLoading, setIsLoading] = useState(false);
    const [sessionId, setSessionId] = useState<string | null>(null);

    // Restore session from localStorage
    useEffect(() => {
        const saved = localStorage.getItem('chatSessionId');
        if (saved) setSessionId(saved);
    }, []);

    // Persist session to localStorage when it changes
    useEffect(() => {
        if (sessionId) localStorage.setItem('chatSessionId', sessionId);
    }, [sessionId]);
    const [showScrollBtn, setShowScrollBtn] = useState(false);
    const [isAuthenticated, setIsAuthenticated] = useState(false);
    const messagesEndRef = useRef<HTMLDivElement>(null);
    const messagesContainerRef = useRef<HTMLDivElement>(null);
    const inputRef = useRef<HTMLInputElement>(null);
    const router = useRouter();

    // Check authentication on mount
    useEffect(() => {
        const token = localStorage.getItem('userToken');
        if (!token) {
            router.push('/login');
        } else {
            setIsAuthenticated(true);
        }
    }, [router]);

    const scrollToBottom = useCallback(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, []);

    useEffect(() => {
        scrollToBottom();
    }, [messages, scrollToBottom]);

    // Track scroll position for "scroll to bottom" button
    useEffect(() => {
        const container = messagesContainerRef.current;
        if (!container) return;
        const handleScroll = () => {
            const { scrollTop, scrollHeight, clientHeight } = container;
            setShowScrollBtn(scrollHeight - scrollTop - clientHeight > 100);
        };
        container.addEventListener("scroll", handleScroll);
        return () => container.removeEventListener("scroll", handleScroll);
    }, []);

    const sendMessage = async (text: string) => {
        if (!text.trim() || isLoading) return;

        const token = localStorage.getItem('userToken');
        if (!token) {
            router.push('/login');
            return;
        }

        const userMessage: Message = {
            id: Date.now().toString(),
            role: "user",
            content: text,
            timestamp: new Date(),
        };

        setMessages((prev) => [...prev, userMessage]);
        setInput("");
        setIsLoading(true);

        // Create empty assistant message to stream into
        const assistantId = (Date.now() + 1).toString();
        setMessages((prev) => [...prev, {
            id: assistantId,
            role: "assistant",
            content: "",
            agent: "TriageAgent",
            timestamp: new Date(),
        }]);

        try {
            const response = await fetch("/api/ai/chat/stream", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${token}`,
                },
                body: JSON.stringify({
                    message: text,
                    session_id: sessionId,
                }),
            });

            if (response.status === 401) {
                localStorage.removeItem('userToken');
                localStorage.removeItem('userData');
                router.push('/login');
                return;
            }

            if (!response.ok || !response.body) {
                throw new Error("Failed to connect to AI service");
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = "";

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split("\n");
                buffer = lines.pop() ?? "";

                for (const line of lines) {
                    if (!line.startsWith("data:")) continue;
                    const raw = line.slice(5).trim();
                    if (!raw) continue;

                    try {
                        const payload = JSON.parse(raw);

                        if (payload.token) {
                            setMessages((prev) => prev.map((m) =>
                                m.id === assistantId
                                    ? { ...m, content: m.content + payload.token, agent: payload.agent || m.agent }
                                    : m
                            ));
                        }

                        if (payload.done) {
                            if (payload.session_id) setSessionId(payload.session_id);
                        }
                    } catch {
                        // skip malformed SSE line
                    }
                }
            }
        } catch {
            setMessages((prev) => prev.map((m) =>
                m.id === assistantId
                    ? { ...m, content: "I'm having trouble connecting right now. Please make sure the backend services are running and try again.", agent: "System" }
                    : m
            ));
        } finally {
            setIsLoading(false);
            inputRef.current?.focus();
        }
    };

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        sendMessage(input);
    };

    const handleQuickAction = (prompt: string) => {
        sendMessage(prompt);
    };

    const handleFeedback = async (messageId: string, rating: "up" | "down") => {
        const token = localStorage.getItem('userToken');
        if (!token) return;
        try {
            await fetch("/api/ai/chat/stream".replace("/stream", "").replace("/chat", "/feedback"), {
                method: "POST",
                headers: { "Content-Type": "application/json", "Authorization": `Bearer ${token}` },
                body: JSON.stringify({ message_id: messageId, rating }),
            });
        } catch {
            // feedback is best-effort
        }
    };

    const formatTime = (date: Date) =>
        date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

    const isFirstLoad = messages.length === 0 && !isLoading;

    return (
        <div className="h-[calc(100vh-5rem)] flex flex-col max-w-5xl mx-auto">
            {/* Header */}
            <div className="flex items-center justify-between px-2 py-3">
                <div className="flex items-center gap-3">
                    <div className="relative">
                        <div className="h-10 w-10 rounded-xl bg-gradient-to-br from-violet-500 to-indigo-600 flex items-center justify-center shadow-lg shadow-violet-500/25">
                            <Bot className="h-5 w-5 text-white" />
                        </div>
                        <div className="absolute -bottom-0.5 -right-0.5 h-3 w-3 rounded-full bg-emerald-400 border-2 border-gray-50" />
                    </div>
                    <div>
                        <h1 className="text-lg font-bold text-gray-900">Event-AI Assistant</h1>
                        <p className="text-xs text-gray-500 flex items-center gap-1">
                            <Sparkles className="h-3 w-3" />
                            Powered by Gemini • Multi-agent system
                        </p>
                    </div>
                </div>
                {sessionId && (
                    <div className="text-[10px] text-gray-400 bg-gray-100 px-2 py-1 rounded-full">
                        Session Active
                    </div>
                )}
            </div>

            {/* Chat Container */}
            <div className="flex-1 rounded-2xl overflow-hidden border border-gray-200 shadow-xl bg-gradient-to-b from-gray-900 via-gray-900 to-gray-950 flex flex-col">
                {/* Messages Area */}
                <div
                    ref={messagesContainerRef}
                    className="flex-1 overflow-y-auto px-4 py-6 space-y-4 relative"
                    style={{
                        scrollbarWidth: "thin",
                        scrollbarColor: "rgba(255,255,255,0.1) transparent",
                    }}
                >
                    {/* Welcome Screen */}
                    {isFirstLoad && (
                        <div className="flex flex-col items-center justify-center h-full text-center animate-fadeIn">
                            <div className="h-16 w-16 rounded-2xl bg-gradient-to-br from-violet-500 to-indigo-600 flex items-center justify-center mb-6 shadow-2xl shadow-violet-500/30">
                                <Sparkles className="h-8 w-8 text-white" />
                            </div>
                            <h2 className="text-2xl font-bold text-white mb-2">
                                Welcome to Event-AI
                            </h2>
                            <p className="text-gray-400 text-sm max-w-md mb-8">
                                Your AI-powered event planning assistant. Plan events, find
                                vendors, book services — all through conversation.
                            </p>

                            {/* Quick Actions Grid */}
                            <div className="grid grid-cols-2 gap-3 w-full max-w-md">
                                {QUICK_ACTIONS.map((action) => (
                                    <button
                                        key={action.label}
                                        onClick={() => handleQuickAction(action.prompt)}
                                        className="group relative flex items-center gap-3 px-4 py-3 rounded-xl bg-white/5 border border-white/10 hover:bg-white/10 hover:border-white/20 transition-all duration-300 text-left"
                                    >
                                        <div
                                            className={`h-9 w-9 rounded-lg bg-gradient-to-br ${action.color} flex items-center justify-center flex-shrink-0 shadow-lg group-hover:scale-105 transition-transform`}
                                        >
                                            <action.icon className="h-4 w-4 text-white" />
                                        </div>
                                        <div>
                                            <div className="text-sm font-medium text-white">
                                                {action.label}
                                            </div>
                                        </div>
                                    </button>
                                ))}
                            </div>

                            <p className="text-gray-500 text-xs mt-6">
                                Or just type a message to get started
                            </p>
                        </div>
                    )}

                    {/* Message List */}
                    {messages.map((message, idx) => (
                        <div
                            key={message.id}
                            className={`flex w-full animate-slideIn ${message.role === "user" ? "justify-end" : "justify-start"
                                }`}
                            style={{ animationDelay: `${idx * 30}ms` }}
                        >
                            {message.role === "assistant" && (
                                <div className="flex-shrink-0 mr-3 mt-1">
                                    <div
                                        className={`h-8 w-8 rounded-lg bg-gradient-to-br ${getAgentColor(
                                            message.agent
                                        )} flex items-center justify-center shadow-lg`}
                                    >
                                        <Bot className="h-4 w-4 text-white" />
                                    </div>
                                </div>
                            )}

                            <div
                                className={`max-w-[75%] ${message.role === "user"
                                        ? "bg-gradient-to-r from-violet-600 to-indigo-600 text-white rounded-2xl rounded-br-md shadow-lg shadow-violet-500/20"
                                        : "bg-white/[0.07] backdrop-blur-sm text-gray-200 rounded-2xl rounded-bl-md border border-white/[0.08]"
                                    } px-4 py-3`}
                            >
                                {/* Agent Badge */}
                                {message.agent && message.role === "assistant" && (
                                    <div className="flex items-center gap-1.5 mb-2">
                                        <Zap className="h-3 w-3 text-yellow-400" />
                                        <span
                                            className={`text-[10px] font-medium px-2 py-0.5 rounded-full bg-gradient-to-r ${getAgentColor(
                                                message.agent
                                            )} text-white`}
                                        >
                                            {getAgentDisplayName(message.agent)}
                                        </span>
                                    </div>
                                )}

                                {/* Content */}
                                <div className="whitespace-pre-wrap break-words">
                                    {message.role === "assistant"
                                        ? renderMarkdown(message.content)
                                        : message.content}
                                </div>

                                {/* Timestamp */}
                                <div
                                    className={`text-[10px] mt-2 flex items-center gap-2 ${message.role === "user"
                                            ? "text-white/50 justify-end"
                                            : "text-gray-500"
                                        }`}
                                >
                                    <span>{formatTime(message.timestamp)}</span>
                                    {message.role === "assistant" && (
                                        <div className="flex gap-1 ml-auto">
                                            <button
                                                onClick={() => handleFeedback(message.id, "up")}
                                                className="hover:text-emerald-400 transition-colors"
                                                title="Helpful"
                                            >👍</button>
                                            <button
                                                onClick={() => handleFeedback(message.id, "down")}
                                                className="hover:text-red-400 transition-colors"
                                                title="Not helpful"
                                            >👎</button>
                                        </div>
                                    )}
                                </div>
                            </div>

                            {message.role === "user" && (
                                <div className="flex-shrink-0 ml-3 mt-1">
                                    <div className="h-8 w-8 rounded-lg bg-gradient-to-br from-gray-600 to-gray-700 flex items-center justify-center">
                                        <User className="h-4 w-4 text-white" />
                                    </div>
                                </div>
                            )}
                        </div>
                    ))}

                    {/* Typing Indicator */}
                    {isLoading && (
                        <div className="flex justify-start animate-slideIn">
                            <div className="flex-shrink-0 mr-3 mt-1">
                                <div className="h-8 w-8 rounded-lg bg-gradient-to-br from-violet-500 to-indigo-600 flex items-center justify-center shadow-lg">
                                    <Bot className="h-4 w-4 text-white" />
                                </div>
                            </div>
                            <div className="bg-white/[0.07] backdrop-blur-sm rounded-2xl rounded-bl-md border border-white/[0.08] px-5 py-4">
                                <div className="flex items-center gap-2">
                                    <div className="flex gap-1">
                                        <span className="h-2 w-2 rounded-full bg-violet-400 animate-bounce" style={{ animationDelay: "0ms" }} />
                                        <span className="h-2 w-2 rounded-full bg-violet-400 animate-bounce" style={{ animationDelay: "150ms" }} />
                                        <span className="h-2 w-2 rounded-full bg-violet-400 animate-bounce" style={{ animationDelay: "300ms" }} />
                                    </div>
                                    <span className="text-xs text-gray-400 ml-2">
                                        Processing your request...
                                    </span>
                                </div>
                            </div>
                        </div>
                    )}

                    <div ref={messagesEndRef} />
                </div>

                {/* Scroll to Bottom */}
                {showScrollBtn && (
                    <div className="flex justify-center -mt-12 mb-2 relative z-10">
                        <button
                            onClick={scrollToBottom}
                            className="bg-white/10 backdrop-blur-md border border-white/20 rounded-full p-2 hover:bg-white/20 transition-all shadow-lg"
                        >
                            <ChevronDown className="h-4 w-4 text-white" />
                        </button>
                    </div>
                )}

                {/* Quick Action Pills (shown when messages exist) */}
                {messages.length > 0 && !isLoading && (
                    <div className="px-4 pb-2 flex gap-2 overflow-x-auto" style={{ scrollbarWidth: "none" }}>
                        {QUICK_ACTIONS.map((action) => (
                            <button
                                key={action.label}
                                onClick={() => handleQuickAction(action.prompt)}
                                className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-white/5 border border-white/10 hover:bg-white/10 transition-all text-xs text-gray-400 hover:text-white whitespace-nowrap flex-shrink-0"
                            >
                                <action.icon className="h-3 w-3" />
                                {action.label}
                            </button>
                        ))}
                    </div>
                )}

                {/* Input Area */}
                <div className="p-4 border-t border-white/[0.08] bg-gray-900/80 backdrop-blur-xl">
                    <form onSubmit={handleSubmit} className="flex gap-3">
                        <div className="flex-1 relative">
                            <input
                                ref={inputRef}
                                type="text"
                                value={input}
                                onChange={(e) => setInput(e.target.value)}
                                placeholder="Message Event-AI..."
                                className="w-full bg-white/[0.07] border border-white/[0.1] rounded-xl px-4 py-3 text-sm text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-violet-500/40 focus:border-violet-500/40 transition-all"
                                disabled={isLoading}
                                autoFocus
                            />
                            <div className="absolute right-3 top-1/2 -translate-y-1/2">
                                <MessageSquare className="h-4 w-4 text-gray-600" />
                            </div>
                        </div>
                        <button
                            type="submit"
                            disabled={isLoading || !input.trim()}
                            className="h-[46px] w-[46px] rounded-xl bg-gradient-to-r from-violet-600 to-indigo-600 flex items-center justify-center text-white shadow-lg shadow-violet-500/25 hover:shadow-violet-500/40 hover:scale-105 active:scale-95 transition-all disabled:opacity-40 disabled:shadow-none disabled:hover:scale-100"
                        >
                            {isLoading ? (
                                <Loader2 className="h-4 w-4 animate-spin" />
                            ) : (
                                <Send className="h-4 w-4" />
                            )}
                        </button>
                    </form>
                </div>
            </div>
        </div>
    );
}
