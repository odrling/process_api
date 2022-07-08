import asyncio
from asyncio.exceptions import CancelledError
import traceback
from typing import Iterable

import aiofiles.os
import aiofiles.tempfile
from fastapi import FastAPI
from pydantic.dataclasses import dataclass
from contextlib import suppress


@dataclass
class Result:
    result: str
    error: bool


_last_clean = 0


def _clean_license():
    global _last_clean
    loop = asyncio.get_running_loop()

    if Simulation._simulation_lock.locked():
        Simulation._simulation_lock.release()
    _last_clean = loop.time()


async def clean_license():
    loop = asyncio.get_running_loop()
    try:
        await aiofiles.os.remove("/tmp/plm.pid")
        _clean_license()
    except FileNotFoundError:
        if _last_clean - loop.time() > 5:
            # assume the file was already deleted by an external process
            _clean_license()


simulation_done = asyncio.Event()


async def license_clean_loop():
    while True:
        try:
            with suppress(asyncio.TimeoutError):
                await asyncio.wait_for(simulation_done.wait(), 1/16)
                simulation_done.clear()

            await clean_license()
        except CancelledError:
            return
        except Exception:
            traceback.print_exc()


@dataclass
class Simulation:
    bpmn_model: str
    bpsim_model: str | None = None
    diagram: str | int | None = None
    scenarios: Iterable[str] | None = None

    _simulation_lock = asyncio.BoundedSemaphore(1)

    async def simulate(self):
        cmd = "pragmaprocesscommand", "simulate"
        if self.diagram is not None:
            cmd += "-d", str(self.diagram)
        if self.scenarios is not None:
            cmd += "-s", ",".join(self.scenarios)

        async with aiofiles.tempfile.NamedTemporaryFile(suffix=".bpmn", mode='r') as result_file:
            async with aiofiles.tempfile.NamedTemporaryFile(suffix=".bpmn", mode='w') as bpmn_file:
                await bpmn_file.write(self.bpmn_model)
                await bpmn_file.flush()

                result_filename: str = result_file.name
                bpmn_filename: str = bpmn_file.name

                cmd += "-o", result_filename, bpmn_filename,
                if self.bpsim_model is not None:
                    cmd += self.bpsim_model,

                await self._simulation_lock.acquire()

                print("running", *cmd)

                proc = await asyncio.create_subprocess_exec(*cmd,
                                                            stdout=asyncio.subprocess.PIPE,
                                                            stderr=asyncio.subprocess.PIPE)
                return_code = await proc.wait()
                simulation_done.set()

                assert proc.stderr is not None
                error_msg = ""
                while not proc.stderr.at_eof():
                    line = await proc.stderr.readline()
                    error_msg += line.decode()

                print(error_msg)

                if return_code != 0:
                    return Result(result=error_msg, error=True)

                return Result(result=await result_file.read(), error=False)


app = FastAPI(title="Process Simulation API",
              description="",
              docs_url="/docs",
              openapi_url="/openapi.json",
              redoc_url="/redoc")


@app.on_event("startup")
async def startup():
    loop = asyncio.get_running_loop()
    loop.create_task(license_clean_loop())


@app.post("/simulate")
async def simulate_api(simulation: Simulation) -> Result:
    return await simulation.simulate()
