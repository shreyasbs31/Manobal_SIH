import { createServer } from "node:http";
import { timingSafeEqual } from "node:crypto";
import { jwtVerify } from "jose";
import { WebSocketServer } from "ws";

const port = Number.parseInt(process.env.PORT ?? "8080", 10);
const secretText = process.env.JWT_SECRET ?? "";
if (secretText.length < 16) {
  throw new Error("JWT_SECRET must contain at least 16 characters");
}
const secret = new TextEncoder().encode(secretText);
const clients = new Map();
const aggregateGroups = new Set(["role:commander", "role:hq"]);
const individualKeys = new Set([
  "token",
  "subject_token",
  "case_id",
  "person_id",
]);

function json(response, status, value) {
  response.writeHead(status, { "content-type": "application/json" });
  response.end(JSON.stringify(value));
}

function equalSecret(candidate) {
  const left = Buffer.from(candidate);
  const right = Buffer.from(secretText);
  return left.length === right.length && timingSafeEqual(left, right);
}

function containsIndividualKey(value) {
  if (Array.isArray(value)) {
    return value.some(containsIndividualKey);
  }
  if (value && typeof value === "object") {
    return Object.entries(value).some(
      ([key, nested]) =>
        individualKeys.has(key.toLowerCase()) || containsIndividualKey(nested),
    );
  }
  return false;
}

async function readJson(request) {
  const chunks = [];
  let length = 0;
  for await (const chunk of request) {
    length += chunk.length;
    if (length > 65_536) {
      throw new Error("Request is too large");
    }
    chunks.push(chunk);
  }
  return JSON.parse(Buffer.concat(chunks).toString("utf8"));
}

const server = createServer(async (request, response) => {
  if (request.method === "GET" && request.url === "/health") {
    json(response, 200, { status: "ok", connections: clients.size });
    return;
  }

  if (request.method === "POST" && request.url === "/publish") {
    const authorization = request.headers.authorization ?? "";
    if (!authorization.startsWith("Bearer ") || !equalSecret(authorization.slice(7))) {
      json(response, 401, {
        error: { code: "unauthorized", message: "Publisher token is invalid" },
      });
      return;
    }

    try {
      const message = await readJson(request);
      const groups = Array.isArray(message.groups) ? message.groups : [];
      if (
        groups.some((group) => aggregateGroups.has(group)) &&
        containsIndividualKey(message.payload)
      ) {
        json(response, 400, {
          error: {
            code: "aggregate_payload_rejected",
            message: "Aggregate groups cannot receive individual fields",
          },
        });
        return;
      }

      const packet = JSON.stringify({
        type: message.type,
        payload: message.payload ?? {},
        at: new Date().toISOString(),
      });
      let delivered = 0;
      for (const [client, allowedGroups] of clients.entries()) {
        if (
          client.readyState === client.OPEN &&
          groups.some((group) => allowedGroups.has(group))
        ) {
          client.send(packet);
          delivered += 1;
        }
      }
      json(response, 202, { delivered });
    } catch {
      json(response, 400, {
        error: { code: "invalid_request", message: "Publish body is invalid" },
      });
    }
    return;
  }

  json(response, 404, {
    error: { code: "not_found", message: "Route not found" },
  });
});

const sockets = new WebSocketServer({ noServer: true });
server.on("upgrade", async (request, socket, head) => {
  try {
    const url = new URL(request.url ?? "/", "http://local");
    const token = url.searchParams.get("token");
    if (!token) {
      throw new Error("Missing token");
    }
    const { payload } = await jwtVerify(token, secret, {
      audience: "manobal-realtime",
      issuer: "manobal-engine",
    });
    const groups = Array.isArray(payload.groups)
      ? payload.groups.filter((group) => typeof group === "string")
      : [];
    if (groups.length === 0) {
      throw new Error("No groups");
    }
    sockets.handleUpgrade(request, socket, head, (client) => {
      clients.set(client, new Set(groups));
      client.on("close", () => clients.delete(client));
      client.send(JSON.stringify({ type: "connected", groups }));
    });
  } catch {
    socket.write("HTTP/1.1 401 Unauthorized\r\nConnection: close\r\n\r\n");
    socket.destroy();
  }
});

server.listen(port, "0.0.0.0", () => {
  console.log(JSON.stringify({ service: "realtime", status: "ready", port }));
});
