import { useEffect, useRef, useState, type FormEvent } from "react";
import {
  Bot,
  ExternalLink,
  MessageCircle,
  Plus,
  Send,
  ShieldCheck,
  ThumbsDown,
  ThumbsUp,
} from "lucide-react";

import {
  assistantService,
  type AssistantConversation,
  type AssistantConversationSummary,
  type AssistantMessage,
} from "../lib/assistant";

const starterQuestions = [
  "What verified schemes may support students?",
  "What documents should I check before applying?",
  "How can I confirm my preliminary eligibility?",
];

function formatDate(value: string | null) {
  if (!value) return "Verification date unavailable";
  return `Verified ${new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
  }).format(new Date(value))}`;
}

export function AssistantPage() {
  const [conversations, setConversations] = useState<
    AssistantConversationSummary[]
  >([]);
  const [activeConversation, setActiveConversation] =
    useState<AssistantConversation | null>(null);
  const [input, setInput] = useState("");
  const [suggestions, setSuggestions] = useState(starterQuestions);
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    let current = true;
    assistantService
      .listConversations()
      .then((items) => {
        if (current) setConversations(items);
      })
      .catch((requestError: unknown) => {
        if (current) {
          setError(
            requestError instanceof Error
              ? requestError.message
              : "Your conversations could not be loaded.",
          );
        }
      })
      .finally(() => {
        if (current) setLoading(false);
      });
    return () => {
      current = false;
    };
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [activeConversation?.messages.length, sending]);

  async function startConversation() {
    setError(null);
    try {
      const conversation = await assistantService.createConversation();
      setActiveConversation(conversation);
      setConversations((items) => [
        { id: conversation.id, title: conversation.title, updated_at: conversation.updated_at },
        ...items,
      ]);
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "A new conversation could not be created.",
      );
    }
  }

  async function openConversation(conversationId: number) {
    setError(null);
    try {
      setActiveConversation(await assistantService.getConversation(conversationId));
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "That conversation could not be loaded.",
      );
    }
  }

  async function submitMessage(message = input) {
    const trimmed = message.trim();
    if (!trimmed || sending) return;
    setSending(true);
    setError(null);
    try {
      const conversation = activeConversation ?? await assistantService.createConversation();
      if (!activeConversation) {
        setConversations((items) => [
          { id: conversation.id, title: conversation.title, updated_at: conversation.updated_at },
          ...items,
        ]);
      }
      const response = await assistantService.sendMessage(conversation.id, trimmed);
      setActiveConversation((current) => ({
        id: response.conversation_id,
        title: current?.title === "New conversation" ? trimmed.slice(0, 200) : current?.title ?? trimmed.slice(0, 200),
        updated_at: new Date().toISOString(),
        messages: [...(current?.messages ?? []), response.user_message, response.assistant_message],
      }));
      setConversations((items) => {
        const next = items.filter((item) => item.id !== response.conversation_id);
        return [
          {
            id: response.conversation_id,
            title: conversation?.title === "New conversation" ? trimmed.slice(0, 200) : conversation?.title ?? trimmed.slice(0, 200),
            updated_at: new Date().toISOString(),
          },
          ...next,
        ];
      });
      setSuggestions(response.suggested_questions);
      if (response.retrieval_warning) setError(response.retrieval_warning);
      setInput("");
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Your question could not be sent. Please try again.",
      );
    } finally {
      setSending(false);
    }
  }

  async function handleFeedback(message: AssistantMessage, feedback: "helpful" | "not_helpful") {
    if (!activeConversation) return;
    try {
      const updated = await assistantService.sendFeedback(activeConversation.id, message.id, feedback);
      setActiveConversation((current) =>
        current
          ? { ...current, messages: current.messages.map((item) => (item.id === updated.id ? updated : item)) }
          : current,
      );
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Feedback could not be saved.");
    }
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void submitMessage();
  }

  return (
    <section className="assistant-page" aria-labelledby="assistant-title">
      <aside className="assistant-sidebar" aria-label="Assistant conversations">
        <div>
          <p className="eyebrow">Guided assistance</p>
          <h1 id="assistant-title">SchemeSathi assistant</h1>
        </div>
        <button className="assistant-new" onClick={() => void startConversation()} type="button">
          <Plus aria-hidden="true" size={17} /> New conversation
        </button>
        <nav className="assistant-conversation-list" aria-label="Previous conversations">
          {loading ? <p>Loading conversations…</p> : conversations.length ? conversations.map((conversation) => (
            <button
              className={activeConversation?.id === conversation.id ? "is-active" : ""}
              key={conversation.id}
              onClick={() => void openConversation(conversation.id)}
              type="button"
            >
              <MessageCircle aria-hidden="true" size={16} />
              <span>{conversation.title || "New conversation"}</span>
            </button>
          )) : <p>Your conversations will appear here.</p>}
        </nav>
      </aside>

      <div className="assistant-chat">
        <header className="assistant-chat-header">
          <span className="assistant-bot-icon"><Bot aria-hidden="true" size={20} /></span>
          <div>
            <h2>Evidence-first guidance</h2>
            <p>Answers cite stored sources and never guarantee approval.</p>
          </div>
        </header>

        <div className="assistant-messages" aria-live="polite">
          {!activeConversation?.messages.length && !sending && (
            <div className="assistant-empty">
              <ShieldCheck aria-hidden="true" size={28} />
              <h2>What would you like to understand?</h2>
              <p>Ask about verified scheme information, documents, application guidance, or preliminary eligibility.</p>
            </div>
          )}
          {activeConversation?.messages.map((message) => (
            <article className={`assistant-message assistant-message--${message.role}`} key={message.id}>
              <p>{message.content}</p>
              {message.role === "assistant" && message.citations.length > 0 && (
                <div className="assistant-source-list" aria-label="Sources supporting this answer">
                  {message.citations.map((citation) => (
                    <a href={citation.url} key={`${message.id}-${citation.source_id}`} rel="noreferrer" target="_blank">
                      <ExternalLink aria-hidden="true" size={14} />
                      <span><strong>{citation.title || citation.document_title || "Verified source"}</strong>{formatDate(citation.last_verified_at)}</span>
                    </a>
                  ))}
                </div>
              )}
              {message.role === "assistant" && (
                <div className="assistant-feedback" aria-label="Rate this answer">
                  <button aria-label="This answer was helpful" className={message.feedback === "helpful" ? "is-selected" : ""} onClick={() => void handleFeedback(message, "helpful")} type="button"><ThumbsUp aria-hidden="true" size={15} /></button>
                  <button aria-label="This answer was not helpful" className={message.feedback === "not_helpful" ? "is-selected" : ""} onClick={() => void handleFeedback(message, "not_helpful")} type="button"><ThumbsDown aria-hidden="true" size={15} /></button>
                </div>
              )}
            </article>
          ))}
          {sending && <div className="assistant-typing"><span /><span /><span /> Thinking with your saved sources…</div>}
          <div ref={bottomRef} />
        </div>

        {error && <p className="assistant-error" role="status">{error}</p>}
        <div className="assistant-suggestions" aria-label="Suggested questions">
          {suggestions.map((question) => <button key={question} onClick={() => void submitMessage(question)} type="button">{question}</button>)}
        </div>
        <form className="assistant-composer" onSubmit={handleSubmit}>
          <label className="visually-hidden" htmlFor="assistant-question">Ask a scheme question</label>
          <textarea disabled={sending} id="assistant-question" maxLength={4000} onChange={(event) => setInput(event.target.value)} placeholder="Ask about a scheme, required documents, or eligibility…" rows={2} value={input} />
          <button aria-label="Send question" disabled={!input.trim() || sending} type="submit"><Send aria-hidden="true" size={18} /></button>
        </form>
        <p className="assistant-disclaimer">Information is general guidance based on retrieved records. Verify details with the cited official source.</p>
      </div>
    </section>
  );
}
