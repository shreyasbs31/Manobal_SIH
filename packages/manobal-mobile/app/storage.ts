import * as SecureStore from "expo-secure-store";

import { memoryStore, type SecretStore } from "../src/session";

const memory = memoryStore();

export const deviceStore: SecretStore = {
  async get(key) {
    try {
      return await SecureStore.getItemAsync(key);
    } catch {
      return memory.get(key);
    }
  },
  async set(key, value) {
    try {
      await SecureStore.setItemAsync(key, value);
    } catch {
      await memory.set(key, value);
    }
  },
  async clear(key) {
    try {
      await SecureStore.deleteItemAsync(key);
    } catch {
      await memory.clear(key);
    }
  },
};
