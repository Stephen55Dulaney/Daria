/**
 * Utility functions for exporting, downloading, and sharing
 */

/**
 * Download JSON data as a file
 */
export const downloadJson = (data: any, filename: string): void => {
  const jsonString = JSON.stringify(data, null, 2);
  const blob = new Blob([jsonString], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  
  // Clean up
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
};

/**
 * Share content via the Web Share API if available
 */
export const shareContent = async (title: string, text: string, url: string): Promise<boolean> => {
  if (navigator.share) {
    try {
      await navigator.share({
        title,
        text,
        url
      });
      return true;
    } catch (error) {
      console.error('Error sharing:', error);
      return false;
    }
  } else {
    // Fallback: copy link to clipboard
    try {
      await navigator.clipboard.writeText(url);
      return true;
    } catch (error) {
      console.error('Failed to copy link:', error);
      return false;
    }
  }
};

/**
 * Generate a Figma-compatible SVG template for a persona
 * This is a placeholder - actual implementation would be more complex
 */
export const generatePersonaSvg = (personaData: any): string => {
  // Placeholder implementation - would actually generate SVG based on persona data
  return `<svg width="800" height="600" xmlns="http://www.w3.org/2000/svg">
    <rect width="100%" height="100%" fill="white"/>
    <text x="50" y="50" font-family="Arial" font-size="24" font-weight="bold">${personaData.name}</text>
    <!-- More SVG elements would be generated based on persona data -->
  </svg>`;
};

/**
 * Generate a Figma-compatible SVG template for a journey map
 * This is a placeholder - actual implementation would be more complex
 */
export const generateJourneyMapSvg = (journeyMapData: any): string => {
  // Placeholder implementation - would actually generate SVG based on journey map data
  const stageWidth = 800 / (journeyMapData.stages?.length || 1);
  
  let stagesSvg = '';
  journeyMapData.stages?.forEach((stage: any, index: number) => {
    const x = index * stageWidth;
    stagesSvg += `
      <g transform="translate(${x}, 100)">
        <rect width="${stageWidth - 10}" height="100" fill="#f0f0f0" stroke="#ccc"/>
        <text x="10" y="30" font-family="Arial" font-size="16" font-weight="bold">${stage.stageTitle}</text>
      </g>
    `;
  });
  
  return `<svg width="800" height="600" xmlns="http://www.w3.org/2000/svg">
    <rect width="100%" height="100%" fill="white"/>
    <text x="50" y="50" font-family="Arial" font-size="24" font-weight="bold">${journeyMapData.journeyTitle || 'Journey Map'}</text>
    ${stagesSvg}
    <!-- More SVG elements would be generated based on journey map data -->
  </svg>`;
};

/**
 * Export to Figma-compatible format
 * This is a simplified implementation - would need to be expanded
 */
export const exportToFigma = (data: any, type: 'persona' | 'journey-map'): void => {
  let svgContent: string;
  let filename: string;
  
  if (type === 'persona') {
    svgContent = generatePersonaSvg(data);
    filename = `${data.name.replace(/\s+/g, '_')}_persona.svg`;
  } else {
    svgContent = generateJourneyMapSvg(data);
    filename = `${(data.journeyTitle || 'Journey_Map').replace(/\s+/g, '_')}.svg`;
  }
  
  // Download the SVG
  const blob = new Blob([svgContent], { type: 'image/svg+xml' });
  const url = URL.createObjectURL(blob);
  
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  
  // Clean up
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}; 