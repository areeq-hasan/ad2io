import { useEffect, useState } from 'react'
import './App.css'

interface Device {
  index: number
  name: string
  serial: string
  identifier: number
  revision: number
}

interface Waveform {
  channel: number,
  function: number,
  frequency: number,
  amplitude: number,
  offset: number,
  symmetry: number,
  phase: number
}

function App() {

  const [devices, setDevices] = useState<Device[] | undefined>(undefined);
  const [activeIndex, setActiveIndex] = useState<number | undefined>(undefined);
  const [active, setActive] = useState<boolean>(false);

  const [generating, setGenerating] = useState<boolean>(false);
  const [generateParameters, setGenerateParameters] = useState<Waveform>({
    channel: 0,
    function: 1,
    frequency: 1000,
    amplitude: 1,
    offset: 0,
    symmetry: 50,
    phase: 0
  });

  useEffect(() => {
    fetch("http://127.0.0.1:5000/devices")
      .then((response) => response.json())
      .then((devicesPayload: Device[]) => {
        setDevices(devicesPayload);
        if (devicesPayload.length > 0) setActiveIndex(devicesPayload[0].index);
      })
  }, []);

  return (
    <div className="App">
      {devices &&
        <div className="stack">
          <h1>Oscilloscope Interface</h1>
          <div className="stack">
            <h2>Device Select</h2>
            <form onSubmit={(event) => {
              event.preventDefault();
              if (!active) fetch(`http://127.0.0.1:5000/device/activate?index=${activeIndex}`).then((response) => { if (response.ok) setActive(true) });
              else fetch("http://127.0.0.1:5000/device/deactivate").then((response) => { if (response.ok) setActive(false) });
            }}>
              <label>
                Choose a device:{" "}
                <select value={activeIndex} onChange={(event) => setActiveIndex(parseInt(event.target.value))} disabled={active}>
                  {devices.map((device) => <option value={device.index}>{device.name} (#{device.serial})</option>)}
                </select>
              </label>
              <button type="submit" disabled={generating}>{!active ? "Activate" : "Deactivate"}</button>
            </form>
          </div>
          {active &&
            <div className="wrapper">
              <div className="stack">
                <h2>Generate</h2>
                <form onSubmit={(event) => {
                  event.preventDefault();
                  if (!generating) fetch(`http://127.0.0.1:5000/device/start?channel=${generateParameters.channel}&function=${generateParameters.function}&frequency=${generateParameters.frequency}&amplitude=${generateParameters.amplitude}&offset=${generateParameters.offset}&symmetry=${generateParameters.symmetry}&phase=${generateParameters.phase}`).then((response) => { if (response.ok) setGenerating(true) });
                  else fetch("http://127.0.0.1:5000/device/stop").then((response) => { if (response.ok) setGenerating(false) });
                }}>
                  <label>
                    Channel:{" "}
                    <select value={generateParameters.channel} onChange={(event) => setGenerateParameters({ ...generateParameters, channel: parseInt(event.target.value) })} disabled={generating}>
                      <option value={0}>Channel 1 (W1)</option>
                      <option value={1}>Channel 2 (W2)</option>
                    </select>
                  </label>
                  <label>
                    Function:{" "}
                    <select value={generateParameters.function} onChange={(event) => setGenerateParameters({ ...generateParameters, function: parseInt(event.target.value) })} disabled={generating}>
                      <option value={0}>DC</option>
                      <option value={1}>Sine</option>
                      <option value={2}>Square</option>
                      <option value={3}>Triangle</option>
                      <option value={4}>Ramp Up</option>
                      <option value={5}>Ramp Down</option>
                      <option value={6}>Noise</option>
                      <option value={7}>Pulse</option>
                      <option value={8}>Trapezium</option>
                      <option value={9}>Sine Power</option>
                    </select>
                  </label>
                  <label>
                    Frequency:{" "}
                    <input type="number" value={generateParameters.frequency} onChange={(event) => setGenerateParameters({ ...generateParameters, frequency: parseFloat(event.target.value) })} disabled={generating} />
                  </label>
                  <label>
                    Amplitude:{" "}
                    <input type="number" value={generateParameters.amplitude} onChange={(event) => setGenerateParameters({ ...generateParameters, amplitude: parseFloat(event.target.value) })} disabled={generating} />
                  </label>
                  <label>
                    Offset:{" "}
                    <input type="number" value={generateParameters.offset} onChange={(event) => setGenerateParameters({ ...generateParameters, offset: parseFloat(event.target.value) })} disabled={generating} />
                  </label>
                  <label>
                    Symmetry:{" "}
                    <input type="number" value={generateParameters.symmetry} onChange={(event) => setGenerateParameters({ ...generateParameters, symmetry: parseFloat(event.target.value) })} disabled={generating} />
                  </label>
                  <label>
                    Phase:{" "}
                    <input type="number" value={generateParameters.phase} onChange={(event) => setGenerateParameters({ ...generateParameters, phase: parseFloat(event.target.value) })} disabled={generating} />
                  </label>
                  <button type="submit">{!generating ? "Start" : "Stop"}</button>
                </form>
              </div>
              <div className="stack">
                <h2>Acquire</h2>
                <img src={generating ? "http://127.0.0.1:5000/device/stream" : ""}></img>
              </div>
            </div>
          }
        </div>
      }
    </div >
  )
}

export default App
