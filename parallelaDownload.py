import aiohttp
import aiofiles
import asyncio
import os
import time
from tqdm import tqdm
 
async def download_range(session, url, start, end, part_num, progress, speeds):
    headers = {'Range': f'bytes={start}-{end}'}
    filename = f"part_{part_num}.tmp"
    try:
        async with session.get(url, headers=headers) as resp:
            async with aiofiles.open(filename, 'wb') as f:
                downloaded = 0
                start_time = time.time()
                async for chunk in resp.content.iter_chunked(1024 * 64):  # 64KB chunks
                    await f.write(chunk)
                    chunk_size = len(chunk)
                    downloaded += chunk_size
                    progress.update(chunk_size)
                elapsed = time.time() - start_time
                speeds[part_num] = downloaded / elapsed if elapsed > 0 else 0
        return filename
    except Exception as e:
        print(f"[Error] Part {part_num} failed: {e}")
        raise
 
async def download_zip_parallel(url, output_file, num_parts=16):
    # Disable all timeouts
    timeout = aiohttp.ClientTimeout(total=None)
    connector = aiohttp.TCPConnector(limit_per_host=num_parts)
 
    async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
        async with session.head(url) as resp:
            if 'Content-Length' not in resp.headers:
                raise Exception("Missing Content-Length header.")
            file_size = int(resp.headers['Content-Length'])
 
        # Setup progress bar
        progress = tqdm(total=file_size, unit='B', unit_scale=True, desc='Downloading', ncols=100)
        part_size = file_size // num_parts
        speeds = [0] * num_parts
        tasks = []
 
        for i in range(num_parts):
            start = i * part_size
            end = file_size - 1 if i == num_parts - 1 else (start + part_size - 1)
            tasks.append(download_range(session, url, start, end, i, progress, speeds))
 
        try:
            part_files = await asyncio.gather(*tasks)
        finally:
            progress.close()
 
        avg_speed = sum(speeds) / len(speeds) / (1024 * 1024)
        print(f"\nAverage speed: {avg_speed:.2f} MB/s")
 
        # Merge all parts
        async with aiofiles.open(output_file, 'wb') as output:
            for part_file in part_files:
                async with aiofiles.open(part_file, 'rb') as pf:
                    await output.write(await pf.read())
                os.remove(part_file)
 
        print(f"✅ Download completed: {output_file}")
 
# Usage
if __name__ == '__main__':
    url = "https://iwm.dhe.ibm.com/sdfdl/v2/regs2/mbford/Xa.2/Xb.WJL1CuPI9hrFOjfURNGpgaRCbSTunueem8D1eti2AhE/Xc.13.0.3.0-ACE-WIN64-EVALUATION.zip/Xd./Xf.lPr.D1vk/Xg.13385323/Xi.swg-wmbfd/XY.regsrvs/XZ.3senR2BbentYTy0xwbUkHpiCrTy_i3nm/13.0.3.0-ACE-WIN64-EVALUATION.zip"  # Replace with actual ZIP URL
    asyncio.run(download_zip_parallel(url, "13.0.3.0-ACE-WIN64-EVALUATION.zip"))
