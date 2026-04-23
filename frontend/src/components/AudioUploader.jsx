import React, { useState, useRef } from 'react';
import { Upload, X, Music } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { toast } from 'react-hot-toast';

const MAX_FILE_SIZE = 5 * 1024 * 1024;

const AudioUploader = ({ onFileSelect, initialFileName }) => {
  const [file, setFile] = useState(null);
  const [fileName, setFileName] = useState(initialFileName || null);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef(null);

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0];
    if (selectedFile) {
      if (!selectedFile.type.startsWith('audio/')) {
        toast.error('Please select a valid audio file (.mp3, .wav, .ogg)');
        return;
      }
      if (selectedFile.size > MAX_FILE_SIZE) {
        toast.error('File size exceeds the 5MB limit');
        return;
      }
      setFile(selectedFile);
      setFileName(selectedFile.name);
      onFileSelect(selectedFile);
    }
  };

  const handleRemove = () => {
    setFile(null);
    setFileName(null);
    onFileSelect(null);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const onDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const onDragLeave = () => {
    setIsDragging(false);
  };

  const onDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    const selectedFile = e.dataTransfer.files[0];
    if (!selectedFile) return;
    if (!selectedFile.type.startsWith('audio/')) {
      toast.error('Please select a valid audio file (.mp3, .wav, .ogg)');
      return;
    }
    if (selectedFile.size > MAX_FILE_SIZE) {
      toast.error('File size exceeds the 5MB limit');
      return;
    }
    setFile(selectedFile);
    setFileName(selectedFile.name);
    onFileSelect(selectedFile);
  };

  return (
    <div className="space-y-4">
      <label className="text-sm font-medium text-slate-300">Upload Audio File</label>
      
      {!fileName ? (
        <div
          onDragOver={onDragOver}
          onDragLeave={onDragLeave}
          onDrop={onDrop}
          onClick={() => fileInputRef.current.click()}
          className={`glass-card rounded-xl p-8 border-dashed border-2 transition-all cursor-pointer flex flex-col items-center justify-center min-h-[160px] ${
            isDragging ? 'border-primary-500 bg-primary-500/10' : 'border-white/10 hover:border-white/20'
          }`}
        >
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileChange}
            accept="audio/*"
            className="hidden"
          />
          <div className="bg-white/5 p-4 rounded-full mb-4 group-hover:bg-white/10 transition-colors">
            <Upload className="w-8 h-8 text-slate-400" />
          </div>
          <p className="text-slate-300 font-medium">Click or drag & drop</p>
          <p className="text-slate-500 text-sm mt-1">MP3, WAV, or OGG (max 5MB)</p>
        </div>
      ) : (
        <motion.div 
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="glass-card rounded-xl p-4 border border-primary-500/20 bg-primary-500/5 flex items-center justify-between"
        >
          <div className="flex items-center gap-4">
            <div className="bg-primary-500/20 p-2 rounded-lg">
              <Music className="w-6 h-6 text-primary-400" />
            </div>
            <div className="flex flex-col">
              <span className="text-sm font-medium text-white truncate max-w-[200px]">{fileName}</span>
              {file && <span className="text-xs text-slate-400">{(file.size / (1024 * 1024)).toFixed(2)} MB</span>}
            </div>
          </div>
          <button
            type="button"
            onClick={handleRemove}
            className="p-2 hover:bg-white/10 rounded-full text-slate-400 hover:text-white transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </motion.div>
      )}
    </div>
  );
};

export default AudioUploader;
