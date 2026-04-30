declare module "smiles-drawer" {
  export interface DrawerOptions {
    width?: number;
    height?: number;
    bondThickness?: number;
    bondLength?: number;
    shortBondLength?: number;
    bondSpacing?: number;
    atomVisualization?: "default" | "balls" | "none";
    isomeric?: boolean;
    debug?: boolean;
    terminalCarbons?: boolean;
    explicitHydrogens?: boolean;
    overlapSensitivity?: number;
    overlapResolutionIterations?: number;
    compactDrawing?: boolean;
    fontSizeLarge?: number;
    fontSizeSmall?: number;
    padding?: number;
    experimental?: boolean;
    themes?: Record<string, Record<string, string>>;
  }

  export class Drawer {
    constructor(options: DrawerOptions);
    draw(
      tree: unknown,
      canvas: HTMLCanvasElement | null,
      theme?: string,
      infoOnly?: boolean
    ): void;
  }

  export function parse(
    smiles: string,
    successCallback: (tree: unknown) => void,
    errorCallback?: (error: unknown) => void
  ): void;

  const SmilesDrawer: {
    Drawer: typeof Drawer;
    parse: typeof parse;
  };
  export default SmilesDrawer;
}
