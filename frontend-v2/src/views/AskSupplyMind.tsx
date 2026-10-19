import { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  Sparkles, Send, Bot, User, ArrowRight, 
  RefreshCw, Loader2 
} from 'lucide-react';
import clsx from 'clsx';
import toast from 'react-hot-toast';

import { useAssistantChatMutation, useAssistantSuggestions } from '../hooks/useDashboardQueries';

interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  citations?: Array<{
    title: string;
    entity_type: string;
    entity_id: string;
    url: string;
    badge_label: string;
  }>;
  suggested_followups?: string[];
  timestamp: string;
}

export default function AskSupplyMind() {
  const navigate = useNavigate();
  const chatMutation = useAssistantChatMutation();
  const { data: suggestionsData } = useAssistantSuggestions();

  const [inputQuestion, setInputQuestion] = useState('');
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 'welcome',
      role: 'assistant',
      content: 
        "Hello! I am **Ask SupplyMind**, your data-grounded supply chain co-pilot.\n\n" +
        "I query live database records, TFT demand forecasts, LightGBM risk models, and what-if simulation engines to answer your operational questions without hallucinations.\n\n" +
        "Ask me anything or click a suggested prompt below to begin.",
      suggested_followups: [
        "Which suppliers currently have the highest risk?",
        "Which products may experience stockouts soon?",
        "What happens if demand increases by 20%?",
        "Which reorder recommendations should be reviewed first?",
      ],
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    },
  ]);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, chatMutation.isPending]);

  const handleSend = async (questionText?: string) => {
    const text = (questionText || inputQuestion).trim();
    if (!text || chatMutation.isPending) return;

    const userMsg: ChatMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: text,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInputQuestion('');

    try {
      // Build conversation history for API
      const history = messages.slice(-4).map((m) => ({
        role: m.role,
        content: m.content,
      }));

      const res = await chatMutation.mutateAsync({
        question: text,
        history,
      });

      const assistantMsg: ChatMessage = {
        id: `assistant-${Date.now()}`,
        role: 'assistant',
        content: res.answer,
        citations: res.citations,
        suggested_followups: res.suggested_followups,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };

      setMessages((prev) => [...prev, assistantMsg]);
    } catch {
      toast.error('Failed to get assistant response. Please check network.');
      const errorMsg: ChatMessage = {
        id: `assistant-err-${Date.now()}`,
        role: 'assistant',
        content: "I encountered an error querying the database. Please try again or rephrase your question.",
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };
      setMessages((prev) => [...prev, errorMsg]);
    }
  };

  return (
    <div className="h-full flex flex-col p-5 lg:p-6 max-w-4xl mx-auto space-y-4">
      
      {/* Header */}
      <div className="flex items-center justify-between pb-3 border-b border-hairline shrink-0">
        <div className="flex items-center gap-2.5">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-accent-indigo to-cyan-500 flex items-center justify-center text-white shadow-lg shadow-accent-indigo/20">
            <Sparkles size={18} />
          </div>
          <div>
            <h1 className="text-lg font-semibold text-ink flex items-center gap-2">
              Ask SupplyMind
              <span className="text-[10px] font-mono bg-surface-elevated text-muted px-2 py-0.5 rounded-full border border-hairline">
                Grounded Assistant
              </span>
            </h1>
            <p className="text-xs text-muted">
              Live database citations & simulation routing — Free Tier Heuristics
            </p>
          </div>
        </div>

        <button
          onClick={() => setMessages(messages.slice(0, 1))}
          className="btn-secondary !h-8 text-xs flex items-center gap-1.5"
          title="Clear Chat History"
        >
          <RefreshCw size={12} />
          Clear Chat
        </button>
      </div>

      {/* Messages Scroll View */}
      <div className="flex-1 overflow-y-auto space-y-4 pr-1">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={clsx(
              'flex gap-3',
              msg.role === 'user' ? 'justify-end' : 'justify-start'
            )}
          >
            {msg.role === 'assistant' && (
              <div className="w-7 h-7 rounded-lg bg-accent-indigo flex items-center justify-center text-white shrink-0 mt-1">
                <Bot size={15} />
              </div>
            )}

            <div className={clsx(
              'max-w-[85%] rounded-2xl p-4 text-xs leading-relaxed space-y-3',
              msg.role === 'user'
                ? 'bg-accent-indigo text-white rounded-tr-sm ml-8'
                : 'bg-surface-elevated border border-hairline text-ink rounded-tl-sm mr-8 shadow-sm'
            )}>
              {/* Message text with basic markdown formatting */}
              <div className="whitespace-pre-wrap space-y-2">
                {msg.content.split('\n\n').map((paragraph, idx) => (
                  <p key={idx} className="leading-relaxed">
                    {paragraph}
                  </p>
                ))}
              </div>

              {/* Structured Citations */}
              {msg.citations && msg.citations.length > 0 && (
                <div className="pt-2 border-t border-hairline/60">
                  <span className="text-[10px] uppercase font-bold tracking-wider text-muted block mb-2">
                    Verified Citations & Quick Navigation
                  </span>
                  <div className="flex flex-wrap gap-2">
                    {msg.citations.map((c, cIdx) => (
                      <button
                        key={cIdx}
                        onClick={() => navigate(c.url)}
                        className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-surface border border-hairline hover:border-accent-indigo text-slate-200 hover:text-accent-indigo transition-colors text-[11px]"
                      >
                        <span className="font-medium">{c.title}</span>
                        <span className="text-[9px] bg-accent-indigo/20 text-accent-indigo px-1.5 py-0.2 rounded font-mono">
                          {c.badge_label}
                        </span>
                        <ArrowRight size={10} />
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* Follow-up Chips */}
              {msg.suggested_followups && msg.suggested_followups.length > 0 && (
                <div className="pt-2 border-t border-hairline/40">
                  <span className="text-[10px] uppercase font-bold tracking-wider text-muted block mb-1.5">
                    Suggested Next Questions
                  </span>
                  <div className="flex flex-wrap gap-1.5">
                    {msg.suggested_followups.map((f, fIdx) => (
                      <button
                        key={fIdx}
                        onClick={() => handleSend(f)}
                        className="text-[11px] px-2.5 py-1 rounded-full bg-accent-indigo/10 text-slate-300 hover:text-white hover:bg-accent-indigo/25 border border-accent-indigo/20 transition-colors text-left"
                      >
                        {f}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              <span className="text-[9px] text-muted block text-right pt-1">
                {msg.timestamp}
              </span>
            </div>

            {msg.role === 'user' && (
              <div className="w-7 h-7 rounded-lg bg-surface-elevated border border-hairline flex items-center justify-center text-muted shrink-0 mt-1">
                <User size={15} />
              </div>
            )}
          </div>
        ))}

        {chatMutation.isPending && (
          <div className="flex items-center gap-3">
            <div className="w-7 h-7 rounded-lg bg-accent-indigo flex items-center justify-center text-white shrink-0">
              <Bot size={15} />
            </div>
            <div className="bg-surface-elevated border border-hairline rounded-2xl rounded-tl-sm p-3.5 flex items-center gap-2 text-xs text-muted">
              <Loader2 size={14} className="animate-spin text-accent-indigo" />
              <span>Querying operational databases, demand quantiles, and risk matrix...</span>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Suggested Starter Chips */}
      {messages.length === 1 && suggestionsData?.suggestions && (
        <div className="flex flex-wrap gap-1.5 py-1">
          {suggestionsData.suggestions.map((sug: string, idx: number) => (
            <button
              key={idx}
              onClick={() => handleSend(sug)}
              className="text-xs px-3 py-1.5 rounded-xl bg-surface-elevated border border-hairline hover:border-accent-indigo text-slate-300 hover:text-white transition-colors"
            >
              {sug}
            </button>
          ))}
        </div>
      )}

      {/* Input Bar */}
      <div className="shrink-0 pt-2">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSend();
          }}
          className="flex items-center gap-2 bg-surface-elevated border border-hairline rounded-2xl p-2 shadow-lg focus-within:border-accent-indigo"
        >
          <input
            type="text"
            placeholder="Ask about high-risk suppliers, imminent stockouts, or simulate demand shocks..."
            value={inputQuestion}
            onChange={(e) => setInputQuestion(e.target.value)}
            disabled={chatMutation.isPending}
            className="flex-1 bg-transparent px-3 py-1.5 text-xs text-ink focus:outline-none placeholder:text-muted"
          />
          <button
            type="submit"
            disabled={!inputQuestion.trim() || chatMutation.isPending}
            className="w-8 h-8 rounded-xl bg-accent-indigo hover:bg-accent-indigo/90 text-white flex items-center justify-center transition-all disabled:opacity-40 disabled:cursor-not-allowed shrink-0"
          >
            {chatMutation.isPending ? (
              <Loader2 size={14} className="animate-spin" />
            ) : (
              <Send size={14} />
            )}
          </button>
        </form>
        <span className="text-[10px] text-muted text-center block mt-1.5">
          Ask SupplyMind computes responses from verified local records. No external API keys required.
        </span>
      </div>

    </div>
  );
}
