import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Date
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class Listing(Base):
    """
    SQLAlchemy model representing a raw scraped restaurant listing from Swiggy or Zomato.
    """
    __tablename__ = 'listings'

    id = Column(Integer, primary_key=True, autoincrement=True)
    platform = Column(String, nullable=False)          # 'swiggy' | 'zomato'
    brand_name = Column(String, nullable=False)
    url_slug = Column(String, unique=True, nullable=True)
    city = Column(String, nullable=False)
    zone = Column(String, nullable=True)
    address = Column(String, nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    price_range = Column(String, nullable=True)         # '₹' | '₹₹' | '₹₹₹'
    cuisine_tags = Column(String, nullable=True)        # JSON array of strings
    scraped_at = Column(DateTime, default=datetime.datetime.utcnow)
    canonical_brand_id = Column(Integer, nullable=True) # Linked ID for Swiggy/Zomato match

    # Relationships
    fssai_matches = relationship("FssaiMatch", back_populates="listing", cascade="all, delete-orphan")
    anomalies = relationship("Anomaly", back_populates="listing", cascade="all, delete-orphan")
    component = relationship("Component", back_populates="listing", uselist=False, cascade="all, delete-orphan")


class FssaiMatch(Base):
    """
    SQLAlchemy model representing FoSCoS match results for each listing.
    """
    __tablename__ = 'fssai_matches'

    id = Column(Integer, primary_key=True, autoincrement=True)
    listing_id = Column(Integer, ForeignKey('listings.id', ondelete='CASCADE'), nullable=False)
    fssai_name = Column(String, nullable=True)                   # matched FBO name from FoSCoS
    license_no = Column(String, nullable=True)
    license_type = Column(String, nullable=True)                  # 'registration' | 'state' | 'central'
    status = Column(String, nullable=True)                      # 'active' | 'expired' | 'suspended' | 'not_found'
    expiry_date = Column(Date, nullable=True)
    confidence = Column(Float, nullable=True)                   # Jaro-Winkler score 0.0–1.0
    match_type = Column(String, nullable=True)                   # 'exact' | 'fuzzy' | 'no_match'
    queried_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    listing = relationship("Listing", back_populates="fssai_matches")


class Anomaly(Base):
    """
    SQLAlchemy model representing classified compliance anomalies.
    """
    __tablename__ = 'anomalies'

    id = Column(Integer, primary_key=True, autoincrement=True)
    listing_id = Column(Integer, ForeignKey('listings.id', ondelete='CASCADE'), nullable=False)
    anomaly_type = Column(String, nullable=False)          # 'A_no_record' | 'B_expired' | 'C_multi_brand'
    severity = Column(String, nullable=True)               # 'high' | 'medium' | 'low'
    notes = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    listing = relationship("Listing", back_populates="anomalies")


class GraphEdge(Base):
    """
    SQLAlchemy model representing edges between kitchen listings in the network graph.
    """
    __tablename__ = 'graph_edges'

    id = Column(Integer, primary_key=True, autoincrement=True)
    node_a = Column(Integer, ForeignKey('listings.id', ondelete='CASCADE'), nullable=False)
    node_b = Column(Integer, ForeignKey('listings.id', ondelete='CASCADE'), nullable=False)
    edge_type = Column(String, nullable=False)          # 'shared_address' | 'shared_license'
    weight = Column(Float, default=1.0)


class Component(Base):
    """
    SQLAlchemy model representing the network component ID and cluster size for a listing.
    """
    __tablename__ = 'components'

    listing_id = Column(Integer, ForeignKey('listings.id', ondelete='CASCADE'), primary_key=True)
    component_id = Column(Integer, nullable=False)
    component_size = Column(Integer, nullable=False)

    # Relationships
    listing = relationship("Listing", back_populates="component")
