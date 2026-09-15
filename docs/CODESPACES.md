# Codespaces quick start

This fork can run FlyBrain without installing Python or MaleCNS data on the local Mac.

## Start a Codespace

1. Open the repository on GitHub.
2. Choose **Code → Codespaces → Create codespace**.
3. Wait for the container setup to finish. The devcontainer installs the local checkout with development dependencies.
4. In the Codespaces terminal, run:

```bash
bash scripts/codespaces_first_boot.sh
```

The first boot script:

- runs the offline test suite first;
- downloads and verifies the public MaleCNS v1.0 files (about 1.1 GB);
- preprocesses the retained 166,700-neuron connectome;
- runs `tools/real_check.py malecns` with left-eye visual stimulation for 100 simulated ms;
- prints cached dataset information and provenance.

The MaleCNS download/cache lives inside the Codespace, not on the local Mac. Stopping and restarting the same Codespace should keep its storage. Rebuilding or deleting the Codespace may require downloading the data again.

If GitHub offers a machine-size choice, a larger Codespace can make preprocessing more comfortable. The repository intentionally does not auto-download MaleCNS during Codespace creation so that opening a Codespace does not immediately consume bandwidth/storage.

## After the first boot

Useful commands:

```bash
flybrain info malecns
flybrain run examples/hello_brain.py
python tools/real_check.py malecns
```

For custom experiments, keep the scientific boundary explicit: the connectome topology and synapse counts come from reconstructed source data, while LIF dynamics, sensory encoding and motor decoding are model assumptions.
