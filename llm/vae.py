import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler

class VAE(nn.Module):
    def __init__(self, input_dim, hidden_dim, latent_dim):
        super(VAE, self).__init__()
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU()
        )
        self.fc_mean   = nn.Linear(hidden_dim, latent_dim)
        self.fc_logvar = nn.Linear(hidden_dim, latent_dim)
        self.decoder = nn.Sequential(
            nn.Linear(latent_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, input_dim)
            # no sigmoid
        )

    def encode(self, x):
        h = self.encoder(x)
        return self.fc_mean(h), self.fc_logvar(h)

    def reparameterize(self, mean, logvar):
        std = torch.exp(0.5 * logvar)
        eps = torch.randn_like(std)
        return mean + eps * std

    def decode(self, z):
        return self.decoder(z)

    def forward(self, x):
        mean, logvar = self.encode(x)
        z = self.reparameterize(mean, logvar)
        return self.decode(z), mean, logvar

def vae_loss(recon_x, x, mean, logvar):
    # per-element MSE + KL
    recon_loss   = nn.functional.mse_loss(recon_x, x, reduction='mean')
    kl_divergence = -0.5 * torch.sum(1 + logvar - mean.pow(2) - logvar.exp())
    return recon_loss + kl_divergence

def load_dataset(file_path='dataset/UNSW_NB15_training-set.csv', input_dim=None):
    if file_path:
        df = pd.read_csv(file_path)
        cats = df.select_dtypes(include=['object', 'category']).columns
        df = pd.get_dummies(df, columns=cats, drop_first=True)
        features = df.iloc[:, :-1].values
        labels   = df.iloc[:, -1].values
        scaler   = StandardScaler()
        features = scaler.fit_transform(features)
        normal_data = features[labels == 0]
        if input_dim is not None and normal_data.shape[1] != input_dim:
            raise ValueError(
                f"Dataset feature count ({normal_data.shape[1]}) != input_dim ({input_dim})."
            )
        data = torch.tensor(normal_data, dtype=torch.float32)
    else:
        data = torch.tensor(np.random.rand(1000, input_dim).astype(np.float32))
    return DataLoader(TensorDataset(data), batch_size=64, shuffle=True)

def train_vae(model, dataloader, epochs=100, lr=1e-4):
    optimizer = optim.Adam(model.parameters(), lr=lr)
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, factor=0.5, patience=5, verbose=True
    )
    for epoch in range(epochs):
        model.train()
        epoch_loss = 0.0
        for batch in dataloader:
            x = batch[0]
            optimizer.zero_grad()
            recon_x, mean, logvar = model(x)
            loss = vae_loss(recon_x, x, mean, logvar)
            loss.backward()
            # gradient clipping
            nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()
            epoch_loss += loss.item() * x.size(0)
        avg_loss = epoch_loss / len(dataloader.dataset)
        print(f"Epoch {epoch+1:3d} — Loss: {avg_loss:.4f}")
        scheduler.step(avg_loss)

def save_model(model, file_path):
    torch.save(model.state_dict(), file_path)

def load_model(file_path, input_dim, hidden_dim, latent_dim):
    model = VAE(input_dim, hidden_dim, latent_dim)
    model.load_state_dict(torch.load(file_path))
    model.eval()
    return model

def main():
    input_dim  = 201
    hidden_dim = 64
    latent_dim = 100
    dataloader = load_dataset(input_dim=input_dim)
    vae = VAE(input_dim, hidden_dim, latent_dim)
    train_vae(vae, dataloader)
    save_model(vae, "vae_model.pth")

    # quick inference check
    vae = load_model("vae_model.pth", input_dim, hidden_dim, latent_dim)
    example_input = torch.randn(1, input_dim)
    with torch.no_grad():
        recon_x, mean, logvar = vae(example_input)
        print("Reconstructed Output:", recon_x)
        print("Mean:", mean)
        print("Log Variance:", logvar)

if __name__ == "__main__":
    main()
