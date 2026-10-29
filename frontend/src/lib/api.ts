export class ApiError extends Error {
  readonly status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export async function apiRequest<T>(
  path: string,
  init?: RequestInit,
): Promise<T> {
  const baseUrl = import.meta.env.VITE_API_BASE_URL?.trim();
  if (!baseUrl) {
    throw new Error("VITE_API_BASE_URL is not configured.");
  }

  const apiUrl = new URL(baseUrl);
  const localHosts = new Set(["localhost", "127.0.0.1", "[::1]"]);
  if (
    import.meta.env.DEV &&
    localHosts.has(window.location.hostname) &&
    localHosts.has(apiUrl.hostname)
  ) {
    apiUrl.hostname = window.location.hostname;
  }

  const response = await fetch(
    `${apiUrl.toString().replace(/\/+$/, "")}/${path.replace(/^\/+/, "")}`,
    {
      ...init,
      credentials: init?.credentials ?? "include",
      headers: {
        Accept: "application/json",
        ...init?.headers,
      },
    },
  );

  if (!response.ok) {
    let message = `API request failed with status ${response.status}.`;
    try {
      const body: unknown = await response.json();
      if (
        typeof body === "object" &&
        body !== null &&
        "detail" in body &&
        typeof body.detail === "string"
      ) {
        message = body.detail;
      } else if (
        typeof body === "object" &&
        body !== null &&
        "detail" in body &&
        Array.isArray(body.detail)
      ) {
        const messages = body.detail
          .map((item: unknown) =>
            typeof item === "object" &&
            item !== null &&
            "msg" in item &&
            typeof item.msg === "string"
              ? item.msg
              : null,
          )
          .filter((item): item is string => item !== null);
        if (messages.length > 0) {
          message = messages.join(" ");
        }
      }
    } catch {
      message = `API request failed with status ${response.status}.`;
    }
    throw new ApiError(
      message,
      response.status,
    );
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}
