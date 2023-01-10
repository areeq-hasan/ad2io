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

interface Pulse {
  channel: number,
}

function App() {

  const [devices, setDevices] = useState<Device[] | undefined>(undefined);
  const [activeIndex, setActiveIndex] = useState<number | undefined>(undefined);
  const [active, setActive] = useState<boolean>(false);

  const [generating, setGenerating] = useState<boolean>(false);
  const [waveform, setWaveform] = useState<Waveform>({
    channel: 0,
    function: 1,
    frequency: 1000,
    amplitude: 1,
    offset: 0,
    symmetry: 50,
    phase: 0
  });

  const [pulsing, setPulsing] = useState<boolean>(false);
  const [pulse, setPulse] = useState<Pulse>({ channel: 1 });

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
                <h2>Generation</h2>
                <div className="wrapper">
                  <div className="stack">
                    <h3>Waveform</h3>
                    <form onSubmit={(event) => {
                      event.preventDefault();
                      if (!generating) fetch(`http://127.0.0.1:5000/device/start?channel=${waveform.channel}&function=${waveform.function}&frequency=${waveform.frequency}&amplitude=${waveform.amplitude}&offset=${waveform.offset}&symmetry=${waveform.symmetry}&phase=${waveform.phase}`).then((response) => { if (response.ok) setGenerating(true) });
                      else fetch("http://127.0.0.1:5000/device/stop").then((response) => { if (response.ok) setGenerating(false) });
                    }}>
                      <label>
                        Channel:{" "}
                        <select value={waveform.channel} onChange={(event) => setWaveform({ ...waveform, channel: parseInt(event.target.value) })} disabled={generating}>
                          <option value={0}>W1</option>
                          <option value={1}>W2</option>
                        </select>
                      </label>
                      <label>
                        Function:{" "}
                        <select value={waveform.function} onChange={(event) => setWaveform({ ...waveform, function: parseInt(event.target.value) })} disabled={generating}>
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
                        <input type="number" value={waveform.frequency} onChange={(event) => setWaveform({ ...waveform, frequency: parseFloat(event.target.value) })} disabled={generating} />
                      </label>
                      <label>
                        Amplitude:{" "}
                        <input type="number" value={waveform.amplitude} onChange={(event) => setWaveform({ ...waveform, amplitude: parseFloat(event.target.value) })} disabled={generating} />
                      </label>
                      <label>
                        Offset:{" "}
                        <input type="number" value={waveform.offset} onChange={(event) => setWaveform({ ...waveform, offset: parseFloat(event.target.value) })} disabled={generating} />
                      </label>
                      <label>
                        Symmetry:{" "}
                        <input type="number" value={waveform.symmetry} onChange={(event) => setWaveform({ ...waveform, symmetry: parseFloat(event.target.value) })} disabled={generating} />
                      </label>
                      <label>
                        Phase:{" "}
                        <input type="number" value={waveform.phase} onChange={(event) => setWaveform({ ...waveform, phase: parseFloat(event.target.value) })} disabled={generating} />
                      </label>
                      <button type="submit">{!generating ? "Start" : "Stop"}</button>
                    </form>
                  </div>
                  <div className="stack">
                    <h3>Pulse</h3>
                    <form onSubmit={(event) => {
                      event.preventDefault();
                      if (!pulsing) fetch(`http://127.0.0.1:5000/device/pulse/start?channel=${pulse.channel}`).then((response) => { if (response.ok) setPulsing(true) });
                      else fetch(`http://127.0.0.1:5000/device/pulse/stop?channel=${pulse.channel}`).then((response) => { if (response.ok) setPulsing(false) });
                    }}>
                      <label>
                        Channel:{" "}
                        <select value={pulse.channel} onChange={(event) => setPulse({ ...pulse, channel: parseInt(event.target.value) })} disabled={pulsing}>
                          {[...Array(15).keys()].map(i => i + 1).map((index) => <option value={index}>{index}</option>)}
                        </select>
                      </label>
                      <button type="submit">{!pulsing ? "Start" : "Stop"}</button>
                    </form>
                  </div>
                </div>
              </div>
              <div className="stack">
                <h2>Acquisition</h2>
                <img width={640} height={480} src={generating ? "http://127.0.0.1:5000/device/acquire" : ""}></img>
              </div>
            </div>
          }
        </div>
      }
    </div >
  )
}

export default App
