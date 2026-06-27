import { useState } from 'react';
import { Button, Dialog, DialogBody } from '@blueprintjs/core';
import { RunPicker } from './RunPicker';

export function ExportControl() {
  const [open, setOpen] = useState(false);
  return (
    <>
      <Button minimal icon="download" aria-label="Export traces" onClick={() => setOpen(true)} />
      <Dialog
        isOpen={open}
        onClose={() => setOpen(false)}
        title="Export experiment traces"
        icon="download"
      >
        <DialogBody>
          <RunPicker />
        </DialogBody>
      </Dialog>
    </>
  );
}
