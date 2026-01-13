import { useState } from 'react';

export default function CampaignEditor({ campaigns, onChange }) {
  const [newCampaign, setNewCampaign] = useState({
    id: '',
    start: '',
    end: '',
    description_en: '',
    description_es: '',
  });

  const handleAdd = () => {
    if (!newCampaign.id || !newCampaign.start) {
      return;
    }

    const campaign = {
      id: newCampaign.id,
      start: newCampaign.start,
      end: newCampaign.end || null,
      description: {
        en: newCampaign.description_en,
        es: newCampaign.description_es,
      },
    };

    onChange([...campaigns, campaign]);
    setNewCampaign({
      id: '',
      start: '',
      end: '',
      description_en: '',
      description_es: '',
    });
  };

  const handleRemove = (index) => {
    const updated = campaigns.filter((_, i) => i !== index);
    onChange(updated);
  };

  const handleNewChange = (e) => {
    const { name, value } = e.target;
    setNewCampaign((prev) => ({ ...prev, [name]: value }));
  };

  return (
    <div className="campaign-editor">
      {/* Existing Campaigns */}
      {campaigns.length > 0 && (
        <div className="campaigns-list">
          {campaigns.map((campaign, index) => (
            <div key={index} className="campaign-item">
              <div className="campaign-item-header">
                <strong>{campaign.id}</strong>
                <button
                  type="button"
                  className="btn btn-danger btn-small"
                  onClick={() => handleRemove(index)}
                >
                  Remove
                </button>
              </div>
              <div className="campaign-item-details">
                <span>Start: {campaign.start}</span>
                <span>End: {campaign.end || 'Ongoing'}</span>
              </div>
              {campaign.description && (
                <div className="campaign-item-description">
                  {campaign.description.en || campaign.description.es}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Add New Campaign */}
      <div className="campaign-add-form">
        <h5>Add Campaign</h5>
        <div className="form-row">
          <div className="form-group">
            <label className="form-label">Campaign ID</label>
            <input
              type="text"
              name="id"
              value={newCampaign.id}
              onChange={handleNewChange}
              placeholder="e.g., referral_bonus"
            />
          </div>
        </div>
        <div className="form-row">
          <div className="form-group">
            <label className="form-label">Start Date</label>
            <input
              type="date"
              name="start"
              value={newCampaign.start}
              onChange={handleNewChange}
            />
          </div>
          <div className="form-group">
            <label className="form-label">End Date (optional)</label>
            <input
              type="date"
              name="end"
              value={newCampaign.end}
              onChange={handleNewChange}
            />
          </div>
        </div>
        <div className="form-row">
          <div className="form-group">
            <label className="form-label">Description (EN)</label>
            <input
              type="text"
              name="description_en"
              value={newCampaign.description_en}
              onChange={handleNewChange}
              placeholder="Get $10 when you refer a friend!"
            />
          </div>
          <div className="form-group">
            <label className="form-label">Description (ES)</label>
            <input
              type="text"
              name="description_es"
              value={newCampaign.description_es}
              onChange={handleNewChange}
              placeholder="Obtiene $10 cuando refieres a un amigo!"
            />
          </div>
        </div>
        <button
          type="button"
          className="btn btn-secondary btn-small"
          onClick={handleAdd}
          disabled={!newCampaign.id || !newCampaign.start}
        >
          + Add Campaign
        </button>
      </div>
    </div>
  );
}
