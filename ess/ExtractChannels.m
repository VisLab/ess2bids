function [labels, type, X, Y, Z, chaninfo] = ExtractChannels(filename, path)

EEG = pop_loadset(filename, path);

chanlocs = EEG.chanlocs;

labels = {chanlocs.labels};
type = {chanlocs.type};
chaninfo = {EEG.chaninfo}

X = cellfun(@double, {chanlocs.X}, 'UniformOutput', false);
Y = cellfun(@double, {chanlocs.Y}, 'UniformOutput', false);
Z = cellfun(@double, {chanlocs.Z}, 'UniformOutput', false);
