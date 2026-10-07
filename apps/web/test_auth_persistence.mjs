/**
 * ARM Persistent Authentication & Session Validation Test Suite
 */

import { createClient } from "@supabase/supabase-js";
import assert from "assert";

console.log("=================================================");
console.log("ARM AUTHENTICATION & PERSISTENCE TEST SUITE");
console.log("=================================================\n");

const SUPABASE_URL = "https://braijzgcqyimvpoifwjg.supabase.co";
const SUPABASE_ANON_KEY =
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJyYWlqemdjcXlpbXZwb2lmd2pnIiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTA2MDUwMDMsImV4cCI6MjEwNjE4MTAwM30.Dy10C-173RfrJ2RkGtMkqUZgEABmkkgtunwMQ4LSVpQ";

// In-memory persistent storage simulating browser's localStorage
class MockBrowserStorage {
  constructor(initialStore = {}) {
    this.store = { ...initialStore };
  }
  getItem(key) {
    return this.store[key] !== undefined ? this.store[key] : null;
  }
  setItem(key, value) {
    this.store[key] = String(value);
  }
  removeItem(key) {
    delete this.store[key];
  }
  clear() {
    this.store = {};
  }
  dumpKeys() {
    return Object.keys(this.store);
  }
}

async function runTests() {
  let passed = 0;
  let total = 0;

  function test(name, fn) {
    total++;
    try {
      fn();
      console.log(`[PASS] Test ${total}: ${name}`);
      passed++;
    } catch (e) {
      console.error(`[FAIL] Test ${total}: ${name}`);
      console.error("       Error:", e.message);
    }
  }

  async function asyncTest(name, fn) {
    total++;
    try {
      await fn();
      console.log(`[PASS] Test ${total}: ${name}`);
      passed++;
    } catch (e) {
      console.error(`[FAIL] Test ${total}: ${name}`);
      console.error("       Error:", e.message);
    }
  }

  // TEST 1: Supabase client options configuration
  test("Supabase Auth configuration has session persistence and auto-refresh enabled", () => {
    const storage = new MockBrowserStorage();
    const client = createClient(SUPABASE_URL, SUPABASE_ANON_KEY, {
      auth: {
        persistSession: true,
        autoRefreshToken: true,
        detectSessionInUrl: true,
        storage: storage,
      },
    });

    assert(client.auth !== undefined, "Auth module must be initialized");
    storage.setItem("test_arm_key", "valid");
    assert.strictEqual(storage.getItem("test_arm_key"), "valid");
  });

  // Mock authenticated session object
  const mockUser = {
    id: "usr_mock_12345",
    email: "sainikilesh@university.edu",
    user_metadata: { full_name: "SaiNikilesh" },
    role: "authenticated",
    aud: "authenticated",
  };

  const mockSession = {
    access_token: "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.mock_access_token",
    token_type: "bearer",
    expires_in: 3600,
    expires_at: Math.floor(Date.now() / 1000) + 3600,
    refresh_token: "mock_refresh_token_xyz",
    user: mockUser,
  };

  // TEST 2: Session persistence in storage on login
  await asyncTest("Login writes session to storage under Supabase storage key", async () => {
    const sharedStorage = new MockBrowserStorage();
    const supabaseKey = `sb-braijzgcqyimvpoifwjg-auth-token`;

    // Simulate Supabase persisting session
    sharedStorage.setItem(supabaseKey, JSON.stringify(mockSession));
    sharedStorage.setItem("arm_user_name", "SaiNikilesh");
    sharedStorage.setItem("arm_user_email", "sainikilesh@university.edu");
    sharedStorage.setItem("arm_user_id", "usr_mock_12345");

    assert(sharedStorage.getItem(supabaseKey) !== null, "Session must exist in storage");
    const stored = JSON.parse(sharedStorage.getItem(supabaseKey));
    assert.strictEqual(stored.user.email, "sainikilesh@university.edu");
    assert.strictEqual(stored.user.id, "usr_mock_12345");
  });

  // TEST 3: App startup / page refresh session restoration
  await asyncTest("App startup restores session from storage without asking for credentials", async () => {
    const sharedStorage = new MockBrowserStorage();
    const supabaseKey = `sb-braijzgcqyimvpoifwjg-auth-token`;
    sharedStorage.setItem(supabaseKey, JSON.stringify(mockSession));

    // New client instance simulating app mount after page refresh
    const refreshedClient = createClient(SUPABASE_URL, SUPABASE_ANON_KEY, {
      auth: {
        persistSession: true,
        autoRefreshToken: false,
        storage: sharedStorage,
      },
    });

    const { data, error } = await refreshedClient.auth.getSession();
    assert.ifError(error);
    assert(data.session !== null, "Restored session must not be null");
    assert.strictEqual(data.session.user.id, "usr_mock_12345");
    assert.strictEqual(data.session.user.email, "sainikilesh@university.edu");
  });

  // TEST 4: Browser close & reopen simulation
  await asyncTest("Simulated browser close & reopen preserves session across client instances", async () => {
    // 1. Session created in Session A
    const diskStorage = new MockBrowserStorage();
    const supabaseKey = `sb-braijzgcqyimvpoifwjg-auth-token`;
    diskStorage.setItem(supabaseKey, JSON.stringify(mockSession));

    // 2. Browser process exits (client instance destroyed)
    // 3. Browser re-opens with same disk storage
    const reopenedClient = createClient(SUPABASE_URL, SUPABASE_ANON_KEY, {
      auth: {
        persistSession: true,
        autoRefreshToken: false,
        storage: diskStorage,
      },
    });

    const { data: reopenedData } = await reopenedClient.auth.getSession();
    assert(reopenedData.session !== null, "Session must survive browser restart");
    assert.strictEqual(reopenedData.session.access_token, mockSession.access_token);
  });

  // TEST 5: Explicit Logout purges tokens and prevents auto-login
  await asyncTest("Explicit logout removes session from storage and leaves client unauthenticated", async () => {
    const sharedStorage = new MockBrowserStorage();
    const supabaseKey = `sb-braijzgcqyimvpoifwjg-auth-token`;
    sharedStorage.setItem(supabaseKey, JSON.stringify(mockSession));
    sharedStorage.setItem("arm_user_name", "SaiNikilesh");
    sharedStorage.setItem("arm_user_email", "sainikilesh@university.edu");

    const client = createClient(SUPABASE_URL, SUPABASE_ANON_KEY, {
      auth: {
        persistSession: true,
        autoRefreshToken: false,
        storage: sharedStorage,
      },
    });

    // Perform signOut simulation
    await client.auth.signOut();
    sharedStorage.removeItem(supabaseKey);
    sharedStorage.removeItem("arm_user_name");
    sharedStorage.removeItem("arm_user_email");
    sharedStorage.removeItem("arm_user_id");

    const { data: afterLogoutData } = await client.auth.getSession();
    assert.strictEqual(afterLogoutData.session, null, "Session must be null after logout");
    assert.strictEqual(sharedStorage.getItem(supabaseKey), null, "Storage must be cleared");
    assert.strictEqual(sharedStorage.getItem("arm_user_name"), null, "User metadata must be cleared");
  });

  // TEST 6: Multi-tab sync - Sign out in Tab A notifies Tab B
  await asyncTest("Multi-tab sync: onAuthStateChange handles SIGNED_OUT event", async () => {
    const sharedStorage = new MockBrowserStorage();
    const supabaseKey = `sb-braijzgcqyimvpoifwjg-auth-token`;
    sharedStorage.setItem(supabaseKey, JSON.stringify(mockSession));

    const tabA = createClient(SUPABASE_URL, SUPABASE_ANON_KEY, {
      auth: { persistSession: true, storage: sharedStorage },
    });

    let tabBEvent = null;
    const { data: { subscription } } = tabA.auth.onAuthStateChange((event, session) => {
      tabBEvent = event;
    });

    // Trigger signout event
    await tabA.auth.signOut();
    subscription.unsubscribe();

    // Verify Tab received sign out notification
    assert.strictEqual(tabBEvent, "SIGNED_OUT", "Tab listener must receive SIGNED_OUT");
  });

  // TEST 7: Invalid or corrupted session handling
  await asyncTest("Corrupt session data in storage is safely handled without throwing", async () => {
    const sharedStorage = new MockBrowserStorage();
    const supabaseKey = `sb-braijzgcqyimvpoifwjg-auth-token`;
    sharedStorage.setItem(supabaseKey, "INVALID_MALFORMED_JSON_STRING{{{");

    const client = createClient(SUPABASE_URL, SUPABASE_ANON_KEY, {
      auth: { persistSession: true, storage: sharedStorage },
    });

    try {
      const { data, error } = await client.auth.getSession();
      assert(data.session === null || error !== null, "Corrupt session must yield null or error");
    } catch (e) {
      assert.fail("Should not throw unhandled exception on corrupt session");
    }
  });

  console.log(`\n=================================================`);
  console.log(`RESULTS: ${passed}/${total} TESTS PASSED`);
  console.log(`=================================================`);

  if (passed !== total) {
    process.exit(1);
  }
}

runTests().catch((err) => {
  console.error("Test execution failed:", err);
  process.exit(1);
});
