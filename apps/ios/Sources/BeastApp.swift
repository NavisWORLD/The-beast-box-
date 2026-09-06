import SwiftUI

@main
struct BeastApp: App {
    var body: some Scene { WindowGroup { RuntimeView() } }
}

struct RuntimeView: View {
    @State private var input = ""
    @State private var model = "A"
    @State private var receipt = "Loading retained state…"
    @State private var started = false

    private var root: URL {
        FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0]
            .appendingPathComponent("BeastRuntime", isDirectory: true)
    }
    var body: some View {
        NavigationStack {
            Form {
                Section("On-device reference fixture") {
                    Text("Python DurableRuntime retains state on this device. A and B are labelled fixtures; no model weights are bundled.")
                    Picker("Fixture", selection: $model) {
                        Text("A").tag("A")
                        Text("B").tag("B")
                    }
                    TextField("Message", text: $input, axis: .vertical)
                    Button("Send") { run(action: "send") }
                        .disabled(input.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
                    Button("Inspect retained state") { run(action: "inspect") }
                }
                Section("Runtime receipt") {
                    Text(receipt).font(.caption.monospaced()).textSelection(.enabled)
                }
            }
            .navigationTitle("Beast Box")
            .task {
                guard !started else { return }
                started = true
                let args = ProcessInfo.processInfo.arguments
                if let i = args.firstIndex(of: "--acceptance"), args.count > i + 1 {
                    model = args[i + 1]
                    input = "retained iOS acceptance marker \(model)"
                    run(action: "send", acceptance: true)
                } else { run(action: "inspect") }
            }
        }
    }
    @MainActor
    private func run(action: String, acceptance: Bool = false) {
        do {
            let request: [String: String] = ["schema": "beast-ios-v1", "action": action,
                                           "model": model, "text": input]
            let data = try JSONSerialization.data(withJSONObject: request, options: [.sortedKeys])
            receipt = BeastRequest(root.path, String(decoding: data, as: UTF8.self))
            if acceptance {
                let documents = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0]
                try Data(receipt.utf8).write(to: documents.appendingPathComponent("acceptance.json"), options: .atomic)
            }
        } catch { receipt = "Error: \(error.localizedDescription)" }
    }
}
