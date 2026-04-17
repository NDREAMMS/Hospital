import type { ApiError } from "../types";

export function ErrorAlert({ error }: { error: ApiError }) {
  return (
    <div
      style={{
        border: "1px solid rgba(239, 68, 68, 0.4)",
        background: "rgba(239, 68, 68, 0.12)",
        padding: 12,
        borderRadius: 10,
      }}
    >
      <div style={{ fontWeight: 600 }}>Error</div>
      <div style={{ opacity: 0.9 }}>{error.message}</div>
      {error.details ? (
        <pre
          style={{
            margin: "10px 0 0",
            whiteSpace: "pre-wrap",
            opacity: 0.85,
            fontSize: 12,
          }}
        >
          {typeof error.details === "string"
            ? error.details
            : JSON.stringify(error.details, null, 2)}
        </pre>
      ) : null}
    </div>
  );
}
