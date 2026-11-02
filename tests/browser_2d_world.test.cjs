const assert = require("node:assert/strict");
const { readFileSync } = require("node:fs");
const { resolve } = require("node:path");
const { test } = require("node:test");
const vm = require("node:vm");

const html = readFileSync(resolve(__dirname, "../examples/browser_2d_world/index.html"), "utf8");
const script = html.match(/<script>([\s\S]*?)<\/script>/)[1];

function snapshot(lightX = 10, lightY = 5, time = 0) {
  return {
    dataset: "synthetic",
    world: { x: time / 10, y: 1, heading: 0, light_x: lightX, light_y: lightY },
    input: { left: 0.25, right: 0.5 },
    brain: { time_ms: time, step_spikes: 3, cumulative_spikes: 9 },
    action: { speed: 0.5, rotation: 0.1 }
  };
}

async function loadPage() {
  const elements = new Map();
  const context = new Proxy({}, {
    get: (_, name) => name === "createRadialGradient"
      ? () => ({ addColorStop() {} }) : () => {}
  });
  function element(selector) {
    if (!elements.has(selector)) {
      const listeners = new Map();
      const captures = new Set();
      elements.set(selector, {
        width: 720, height: 720, value: "10", checked: false, disabled: false,
        textContent: "",
        getContext: () => context,
        getBoundingClientRect: () => ({ left: 0, top: 0, width: 720, height: 720 }),
        setPointerCapture: id => captures.add(id),
        hasPointerCapture: id => captures.has(id),
        releasePointerCapture: id => captures.delete(id),
        addEventListener: (name, handler) => listeners.set(name, handler),
        emit: (name, event = {}) => listeners.get(name)(event)
      });
    }
    return elements.get(selector);
  }
  const requests = [];
  const scheduled = [];
  const sandbox = vm.createContext({
    document: { querySelector: element },
    fetch: (path, options) => new Promise((resolve, reject) => {
      requests.push({ path, options, reject,
        respond: payload => resolve({ ok: true, json: async () => payload }) });
    }),
    setTimeout: callback => scheduled.push(callback)
  });
  const loaded = vm.runInContext(script, sandbox);
  assert.equal(requests[0].path, "/api/world/state");
  requests.shift().respond(snapshot());
  await loaded;
  const read = expression => JSON.parse(vm.runInContext(`JSON.stringify(${expression})`, sandbox));
  function pointer(name, x, y) {
    element("#world").emit(name, {
      clientX: (x + 12) * 30, clientY: (12 - y) * 30, pointerId: 1
    });
  }
  function drag(x, y, release = true) {
    const world = read("state.world");
    pointer("pointerdown", world.light_x, world.light_y);
    pointer("pointermove", x, y);
    if (release) pointer("pointerup", x, y);
  }
  return { element, requests, read, pointer, drag, scheduled };
}

test("a delayed step keeps a completed drag and sends it on the next step", async () => {
  const page = await loadPage();
  const step = page.element("#step").emit("click");
  const request = page.requests.shift();
  assert.deepEqual(JSON.parse(request.options.body), { light_x: 10, light_y: 5, brain_ms: 10 });
  page.drag(-6, 3);
  request.respond(snapshot(10, 5, 10));
  await step;
  assert.deepEqual(page.read("state.world"), {
    x: 1, y: 1, heading: 0, light_x: -6, light_y: 3
  });
  assert.equal(page.element("#time").textContent, "10 ms");
  assert.equal(page.element("#input-left").textContent, "0.250");
  assert.equal(page.element("#speed").textContent, "0.500");
  assert.deepEqual(page.read("trail"), [{ x: 0, y: 1 }, { x: 1, y: 1 }]);

  const next = page.element("#step").emit("click");
  const nextRequest = page.requests.shift();
  assert.deepEqual(JSON.parse(nextRequest.options.body), { light_x: -6, light_y: 3, brain_ms: 10 });
  nextRequest.respond(snapshot(-6, 3, 20));
  await next;
  assert.equal(page.read("state.brain.time_ms"), 20);
});

test("the latest position wins during an active drag, including world bounds", async () => {
  const page = await loadPage();
  const step = page.element("#step").emit("click");
  page.drag(1, 2, false);
  page.pointer("pointermove", -20, 30);
  page.requests.shift().respond(snapshot(10, 5, 10));
  await step;
  assert.equal(page.read("state.world.light_x"), -12);
  assert.equal(page.read("state.world.light_y"), 12);
  page.pointer("pointermove", 4, -3);
  page.pointer("pointerup", 4, -3);
  assert.equal(page.read("state.world.light_x"), 4);
  assert.equal(page.read("state.world.light_y"), -3);
});

test("an ordinary step applies its response and ignores concurrent step requests", async () => {
  const page = await loadPage();
  const step = page.element("#step").emit("click");
  await page.element("#step").emit("click");
  assert.equal(page.requests.length, 1);
  page.requests.shift().respond(snapshot(10, 5, 10));
  await step;
  assert.deepEqual(page.read("state"), snapshot(10, 5, 10));
  assert.equal(page.element("#step").disabled, false);
  assert.equal(page.element("#reset").disabled, false);
});

test("a failed step preserves a new light position and permits a retry", async () => {
  const page = await loadPage();
  const step = page.element("#step").emit("click");
  page.drag(-4, -2);
  page.requests.shift().reject(new Error("offline fixture"));
  await step;
  assert.equal(page.read("state.world.light_x"), -4);
  assert.equal(page.read("state.brain.time_ms"), 0);
  assert.equal(page.read("busy"), false);
  assert.equal(page.element("#step").disabled, false);
  assert.equal(page.element("#status").textContent, "Error: offline fixture");

  const retry = page.element("#step").emit("click");
  const request = page.requests.shift();
  assert.equal(JSON.parse(request.options.body).light_x, -4);
  request.respond(snapshot(-4, -2, 10));
  await retry;
});

test("Reset still restores the server's default light position", async () => {
  const page = await loadPage();
  page.drag(-6, 3);
  const reset = page.element("#reset").emit("click");
  const request = page.requests.shift();
  assert.equal(request.path, "/api/world/reset");
  request.respond(snapshot());
  await reset;
  assert.deepEqual(page.read("state.world"), snapshot().world);
  assert.deepEqual(page.read("trail"), [{ x: 0, y: 1 }]);
});
