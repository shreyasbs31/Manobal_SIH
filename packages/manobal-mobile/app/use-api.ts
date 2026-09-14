import { useMemo } from "react";

import { createPersonnelClient } from "../src/api/client";
import { defaultApiUrl } from "./config";
import { useSession } from "./session-context";

export function useApi() {
  const { session } = useSession();
  return useMemo(
    () =>
      createPersonnelClient({
        baseUrl: defaultApiUrl(),
        token: session?.token ?? "",
      }),
    [session?.token],
  );
}
