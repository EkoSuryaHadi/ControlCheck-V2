import { Container } from '@cloudflare/containers';

export class ControlCheckApi extends Container {
  defaultPort = 8080;
  sleepAfter = '30m';
  enableInternet = true;
  pingEndpoint = '/api/health';
}

interface Env { CONTROLCHECK_API: DurableObjectNamespace<ControlCheckApi>; }

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const container = env.CONTROLCHECK_API.getByName('controlcheck-api');
    await container.startAndWaitForPorts();
    return container.fetch(request);
  },
};
