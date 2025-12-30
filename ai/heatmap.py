import numpy as np
import cv2

class HeatmapAccumulator:
    """
    Real-time 2D heatmap accumulator for swimmer track activity.
    - Accepts (track_id, bbox, frame_idx) per frame.
    - Maintains a 2D float map (same size as video or resized).
    - Supports Gaussian smoothing for visualization.
    """

    def __init__(self, frame_shape, out_size=None, decay=0.99, gauss_sigma=8):
        """
        :param frame_shape: Shape of input frames as (height, width, channels), e.g. (720,1280,3)
        :param out_size: (height, width) for heatmap output. If None, matches input frame size.
        :param decay: Per-frame decay to fade old tracks (1=no decay; <1 gives 'temporal haze').
        :param gauss_sigma: Standard deviation for gaussian smoothing (pixels).
        """
        self.in_h, self.in_w = frame_shape[:2]
        self.out_h, self.out_w = out_size if out_size is not None else (self.in_h, self.in_w)
        self.decay = decay
        self.gauss_sigma = gauss_sigma

        # Heatmap canvas (float32 for large accumulations)
        self.heatmap = np.zeros((self.out_h, self.out_w), dtype=np.float32)

    def _resize_point(self, x, y):
        """
        Rescales a point from input frame size to heatmap size, if needed.
        """
        x_scaled = int(x * self.out_w / self.in_w)
        y_scaled = int(y * self.out_h / self.in_h)
        return x_scaled, y_scaled

    def update(self, tracked_people, frame_idx):
        """
        Update the heatmap with new tracks for this frame.

        :param tracked_people: List of tracked objects.
            Each should have .bbox attribute (x1, y1, x2, y2) and .track_id.
        :param frame_idx: Current frame number (unused, but passes interface).
        """
        # Apply decay to fade old activity (set decay ~0.99 for strong memory, 0.9 for short memory)
        self.heatmap *= self.decay

        # For each tracked swimmer, increment the heatmap.
        for person in tracked_people:
            # Center of the bbox
            x1, y1, x2, y2 = person.bbox
            cx, cy = (x1 + x2) // 2, (y1 + y2) // 2

            # Resize to heatmap grid if needed
            cx, cy = self._resize_point(cx, cy)

            # Safety check
            if 0 <= cx < self.out_w and 0 <= cy < self.out_h:
                self.heatmap[cy, cx] += 1.0  # Accumulate "activity" at this spatial location

    def get_smoothed(self):
        """
        Returns a version of the heatmap with Gaussian smoothing applied.
        Use this for visualization.
        """
        if self.gauss_sigma > 0:
            smoothed = cv2.GaussianBlur(self.heatmap, (0,0), self.gauss_sigma)
        else:
            smoothed = self.heatmap.copy()
        return smoothed

    def render_overlay(self, base_img, alpha=0.5, colormap=cv2.COLORMAP_JET, normalize=True):
        """
        Renders the current heatmap as an RGB overlay on the base image.

        :param base_img: Input frame (H,W,3), BGR.
        :param alpha: Blend factor heatmap over image.
        :param colormap: OpenCV colormap (e.g., cv2.COLORMAP_JET)
        :param normalize: Whether to auto-normalize the heatmap for display.
        :return: blended output image (BGR).
        """
        heat = self.get_smoothed()

        # Resize heatmap to match base_img size for overlay
        target_h, target_w = base_img.shape[:2]
        heat_resized = cv2.resize(heat, (target_w, target_h), interpolation=cv2.INTER_LINEAR)

        # Normalize heatmap for visualization (0-255)
        if normalize:
            hmin, hmax = np.percentile(heat_resized, 5), np.percentile(heat_resized, 99)
            heat_vis = np.clip((heat_resized - hmin) / (hmax - hmin + 1e-5), 0, 1)
        else:
            heat_vis = np.clip(heat_resized, 0, 1)

        heat_vis = np.uint8(255 * heat_vis)
        heat_color = cv2.applyColorMap(heat_vis, colormap)

        overlay = cv2.addWeighted(base_img, 1 - alpha, heat_color, alpha, 0)
        return overlay

    def get_heatmap_image(self, as_colormap=True, normalize=True, colormap=cv2.COLORMAP_JET):
        """
        Returns the heatmap as an image for saving/display.

        :param as_colormap: If True, return as BGR (colored); else uint8 grayscale.
        :param normalize: If True, auto-normalize to 0-255.
        :param colormap: OpenCV colormap to use.
        :return: heatmap image (BGR or grayscale uint8).
        """
        heat = self.get_smoothed()

        # Normalize to 0-255
        if normalize:
            hmin, hmax = np.percentile(heat, 5), np.percentile(heat, 99)
            heat_vis = np.clip((heat - hmin) / (hmax - hmin + 1e-5), 0, 1)
        else:
            heat_vis = np.clip(heat, 0, 1)
        heat_vis = np.uint8(255 * heat_vis)
        if as_colormap:
            return cv2.applyColorMap(heat_vis, colormap)
        else:
            return heat_vis
