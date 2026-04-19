"""GUI Demo for Fragile Watermarking."""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import numpy as np
from PIL import Image, ImageTk
import threading

from src.watermark_embed import WatermarkEmbedder
from src.watermark_extract import WatermarkAuthenticator
from src.utils import load_image, save_image
from src.metrics import psnr
from tests.test_attacks import cutting_attack


class WatermarkingGUI:
    """Interactive GUI for watermarking demonstration."""
    
    def __init__(self, root):
        self.root = root
        self.root.title("Fragile Watermarking Demo — Group 11")
        self.root.geometry("1200x700")
        
        self.current_image = None
        self.current_stego = None
        self.current_metadata = None
        self.current_attacked = None
        
        # Create tabs
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Tab 1: Embed
        self.tab_embed = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_embed, text="Embed Watermark")
        self._create_embed_tab()
        
        # Tab 2: Attack
        self.tab_attack = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_attack, text="Simulate Attack")
        self._create_attack_tab()
        
        # Tab 3: Authenticate
        self.tab_auth = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_auth, text="Authenticate & Recover")
        self._create_auth_tab()
        
        print("GUI initialized. Ready for interaction.")
    
    def _create_embed_tab(self):
        """Create embedding tab."""
        frame = ttk.Frame(self.tab_embed)
        frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Controls
        controls = ttk.LabelFrame(frame, text="Embedding Controls", padding=10)
        controls.pack(fill="x", padx=5, pady=5)
        
        ttk.Button(controls, text="Load Image", 
                  command=self._load_image).pack(side="left", padx=5)
        
        ttk.Label(controls, text="Seed γ:").pack(side="left", padx=5)
        self.seed_gamma = ttk.Entry(controls, width=5)
        self.seed_gamma.insert(0, "42")
        self.seed_gamma.pack(side="left", padx=2)
        
        ttk.Label(controls, text="Seed γ1:").pack(side="left", padx=5)
        self.seed_gamma1 = ttk.Entry(controls, width=5)
        self.seed_gamma1.insert(0, "123")
        self.seed_gamma1.pack(side="left", padx=2)
        
        ttk.Label(controls, text="Seed γ2:").pack(side="left", padx=5)
        self.seed_gamma2 = ttk.Entry(controls, width=5)
        self.seed_gamma2.insert(0, "456")
        self.seed_gamma2.pack(side="left", padx=2)
        
        ttk.Button(controls, text="Embed Watermark",
                  command=self._embed).pack(side="left", padx=5)
        
        ttk.Button(controls, text="Save Watermarked Image",
                  command=self._save_stego).pack(side="left", padx=5)
        
        # Image display
        display = ttk.LabelFrame(frame, text="Results", padding=10)
        display.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.label_info = ttk.Label(display, text="Load an image to start")
        self.label_info.pack(fill="x", padx=5, pady=5)
        
        canvas_frame = ttk.Frame(display)
        canvas_frame.pack(fill="both", expand=True)
        
        self.canvas_orig = tk.Canvas(canvas_frame, width=256, height=256, bg="gray")
        self.canvas_orig.pack(side="left", padx=10, pady=10)
        ttk.Label(canvas_frame, text="Original").pack(side="left", pady=10)
        
        self.canvas_stego = tk.Canvas(canvas_frame, width=256, height=256, bg="gray")
        self.canvas_stego.pack(side="left", padx=10, pady=10)
        ttk.Label(canvas_frame, text="Watermarked").pack(side="left", pady=10)
        
        ttk.Label(canvas_frame, text="PSNR: --").pack(side="left", padx=10)
    
    def _create_attack_tab(self):
        """Create attack simulation tab."""
        frame = ttk.Frame(self.tab_attack)
        frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Controls
        controls = ttk.LabelFrame(frame, text="Attack Parameters", padding=10)
        controls.pack(fill="x", padx=5, pady=5)
        
        ttk.Label(controls, text="Attack Type:").pack(side="left", padx=5)
        self.attack_type = ttk.Combobox(controls, 
                                        values=["Cutting Attack", "Copy-Paste Attack"],
                                        width=20, state="readonly")
        self.attack_type.current(0)
        self.attack_type.pack(side="left", padx=5)
        
        ttk.Label(controls, text="Start Row:").pack(side="left", padx=5)
        self.attack_row = ttk.Entry(controls, width=5)
        self.attack_row.insert(0, "32")
        self.attack_row.pack(side="left", padx=2)
        
        ttk.Label(controls, text="Start Col:").pack(side="left", padx=5)
        self.attack_col = ttk.Entry(controls, width=5)
        self.attack_col.insert(0, "32")
        self.attack_col.pack(side="left", padx=2)
        
        ttk.Label(controls, text="Height:").pack(side="left", padx=5)
        self.attack_h = ttk.Entry(controls, width=5)
        self.attack_h.insert(0, "64")
        self.attack_h.pack(side="left", padx=2)
        
        ttk.Label(controls, text="Width:").pack(side="left", padx=5)
        self.attack_w = ttk.Entry(controls, width=5)
        self.attack_w.insert(0, "64")
        self.attack_w.pack(side="left", padx=2)
        
        ttk.Button(controls, text="Apply Attack",
                  command=self._apply_attack).pack(side="left", padx=5)
    
    def _create_auth_tab(self):
        """Create authentication & recovery tab."""
        frame = ttk.Frame(self.tab_auth)
        frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Controls
        controls = ttk.LabelFrame(frame, text="Authentication Controls", padding=10)
        controls.pack(fill="x", padx=5, pady=5)
        
        ttk.Button(controls, text="Load Attacked Image",
                  command=self._load_attacked).pack(side="left", padx=5)
        
        ttk.Button(controls, text="Authenticate & Recover",
                  command=self._authenticate).pack(side="left", padx=5)
        
        ttk.Label(controls, text="Post-processing:").pack(side="left", padx=5)
        self.postproc = ttk.Combobox(controls,
                                     values=["None", "Bilateral Filter"],
                                     width=15, state="readonly")
        self.postproc.current(0)
        self.postproc.pack(side="left", padx=5)
        
        # Results
        self.label_metrics = ttk.Label(frame, text="Metrics: --")
        self.label_metrics.pack(fill="x", padx=5, pady=5)
    
    def _load_image(self):
        """Load image for embedding."""
        file = filedialog.askopenfilename(
            filetypes=[("PNG", "*.png"), ("JPG", "*.jpg"), ("All", "*.*")]
        )
        if file:
            try:
                self.current_image = load_image(file, grayscale=True)
                self._display_image(self.canvas_orig, self.current_image)
                self.label_info.config(
                    text=f"Loaded: {file}\nSize: {self.current_image.shape}"
                )
                messagebox.showinfo("Success", f"Image loaded: {self.current_image.shape}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load image: {e}")
    
    def _embed(self):
        """Embed watermark."""
        if self.current_image is None:
            messagebox.showwarning("Warning", "Load an image first")
            return
        
        try:
            gamma = int(self.seed_gamma.get())
            gamma1 = int(self.seed_gamma1.get())
            gamma2 = int(self.seed_gamma2.get())
            
            embedder = WatermarkEmbedder(gamma, gamma1, gamma2)
            stego, metadata = embedder.embed(self.current_image)
            
            self.current_stego = stego
            self.current_metadata = metadata
            
            psnr_val = psnr(self.current_image, stego)
            
            self._display_image(self.canvas_stego, stego)
            self.label_info.config(
                text=f"Embedding complete!\nPSNR: {psnr_val:.2f} dB"
            )
            messagebox.showinfo("Success", f"Watermark embedded!\nPSNR: {psnr_val:.2f} dB")
        except Exception as e:
            messagebox.showerror("Error", f"Embedding failed: {e}")
    
    def _save_stego(self):
        """Save watermarked image."""
        if self.current_stego is None:
            messagebox.showwarning("Warning", "Embed watermark first")
            return
        
        file = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG", "*.png")]
        )
        if file:
            try:
                save_image(file, self.current_stego)
                messagebox.showinfo("Success", f"Saved to {file}")
            except Exception as e:
                messagebox.showerror("Error", f"Save failed: {e}")
    
    def _apply_attack(self):
        """Apply attack on watermarked image."""
        if self.current_stego is None:
            messagebox.showwarning("Warning", "Embed watermark first")
            return
        
        try:
            row = int(self.attack_row.get())
            col = int(self.attack_col.get())
            h = int(self.attack_h.get())
            w = int(self.attack_w.get())
            
            attacked, _ = cutting_attack(self.current_stego, row, col, h, w)
            self.current_attacked = attacked
            
            messagebox.showinfo("Success", f"Attack applied: {h}x{w} region")
        except Exception as e:
            messagebox.showerror("Error", f"Attack failed: {e}")
    
    def _load_attacked(self):
        """Load attacked image."""
        file = filedialog.askopenfilename(
            filetypes=[("PNG", "*.png"), ("JPG", "*.jpg")]
        )
        if file:
            try:
                self.current_attacked = load_image(file, grayscale=True)
                messagebox.showinfo("Success", "Attacked image loaded")
            except Exception as e:
                messagebox.showerror("Error", f"Load failed: {e}")
    
    def _authenticate(self):
        """Authenticate and recover."""
        if self.current_attacked is None:
            messagebox.showwarning("Warning", "Load attacked image first")
            return
        if self.current_metadata is None:
            messagebox.showwarning("Warning", "Embed watermark first")
            return
        
        try:
            authenticator = WatermarkAuthenticator()
            result = authenticator.authenticate_and_recover(
                self.current_attacked,
                self.current_metadata['vq_codebook'],
                self.current_image
            )
            
            metrics = result['metrics']
            msg = f"""
Authentication Results:
TPR: {metrics['TPR']:.4f}
FPR: {metrics['FPR']:.4f}
FNR: {metrics['FNR']:.4f}
PSNR Recovered: {result['psnr_recovered'] or 0:.2f} dB
Tamper Ratio: {result['tamper_ratio']*100:.2f}%
"""
            
            self.label_metrics.config(text=msg.strip())
            messagebox.showinfo("Success", msg)
        except Exception as e:
            messagebox.showerror("Error", f"Authentication failed: {e}")
    
    def _display_image(self, canvas, img_array):
        """Display image on canvas."""
        try:
            # Resize to fit canvas
            img = Image.fromarray(img_array).resize((256, 256), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            canvas.create_image(0, 0, image=photo, anchor="nw")
            canvas.image = photo
        except Exception as e:
            print(f"Display error: {e}")


if __name__ == "__main__":
    root = tk.Tk()
    gui = WatermarkingGUI(root)
    root.mainloop()
